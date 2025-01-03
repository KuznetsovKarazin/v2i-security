import asyncio
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json
import logging
from collections import defaultdict

class MessagePriority(Enum):
    """Message priority levels"""
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3

@dataclass
class QueueMessage:
    """Represents a message in the queue"""
    id: str
    content: Dict
    priority: MessagePriority
    timestamp: datetime
    retries: int = 0
    processing_started: Optional[datetime] = None
    processing_completed: Optional[datetime] = None
    error: Optional[str] = None

class MessageState(Enum):
    """Possible message states"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

class QueueStats:
    """Tracks queue statistics"""
    def __init__(self):
        self.total_received: int = 0
        self.total_processed: int = 0
        self.total_failed: int = 0
        self.total_retried: int = 0
        self.processing_times: List[float] = []
        self.states: Dict[MessageState, int] = defaultdict(int)
        self.priority_counts: Dict[MessagePriority, int] = defaultdict(int)

    def update_processing_time(self, duration: float):
        """Updates processing time statistics"""
        self.processing_times.append(duration)
        if len(self.processing_times) > 1000:
            self.processing_times.pop(0)

    def get_average_processing_time(self) -> float:
        """Calculates average processing time"""
        if not self.processing_times:
            return 0.0
        return sum(self.processing_times) / len(self.processing_times)

class PriorityMessageQueue:
    """Priority-based message queue with reliability features"""
    def __init__(self,
                 max_size: int = 10000,
                 max_retries: int = 3,
                 processing_timeout: int = 30,
                 batch_size: int = 10):
        # Queue configuration
        self.max_size = max_size
        self.max_retries = max_retries
        self.processing_timeout = processing_timeout
        self.batch_size = batch_size

        # Initialize queues for different priorities
        self.queues = {
            priority: asyncio.PriorityQueue(maxsize=max_size)
            for priority in MessagePriority
        }

        # Message tracking
        self.messages: Dict[str, QueueMessage] = {}
        self.message_states: Dict[str, MessageState] = {}

        # Statistics
        self.stats = QueueStats()

        # Setup logging
        self.logger = logging.getLogger("message_queue")

        # Background tasks
        self.cleanup_task: Optional[asyncio.Task] = None
        self.monitoring_task: Optional[asyncio.Task] = None

    async def start(self):
        """Starts queue background tasks"""
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())

    async def stop(self):
        """Stops queue background tasks"""
        if self.cleanup_task:
            self.cleanup_task.cancel()
        if self.monitoring_task:
            self.monitoring_task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(
            self.cleanup_task,
            self.monitoring_task,
            return_exceptions=True
        )

    async def enqueue(self, message: Dict, priority: MessagePriority) -> str:
        """Enqueues a message with given priority"""
        # Generate message ID
        message_id = str(abs(hash(f"{message}{datetime.now()}")))

        # Create queue message
        queue_message = QueueMessage(
            id=message_id,
            content=message,
            priority=priority,
            timestamp=datetime.now()
        )

        # Store message
        self.messages[message_id] = queue_message
        self.message_states[message_id] = MessageState.PENDING

        # Add to priority queue
        await self.queues[priority].put((priority.value, message_id))

        # Update stats
        self.stats.total_received += 1
        self.stats.priority_counts[priority] += 1
        self.stats.states[MessageState.PENDING] += 1

        return message_id

    async def dequeue(self) -> Optional[QueueMessage]:
        """Dequeues highest priority message"""
        for priority in MessagePriority:
            if not self.queues[priority].empty():
                try:
                    _, message_id = await self.queues[priority].get()
                    message = self.messages[message_id]

                    # Update state
                    self._update_message_state(message_id, MessageState.PROCESSING)
                    message.processing_started = datetime.now()

                    return message
                except Exception as e:
                    self.logger.error(f"Error dequeuing message: {str(e)}")

        return None

    async def dequeue_batch(self) -> List[QueueMessage]:
        """Dequeues a batch of messages"""
        batch = []
        while len(batch) < self.batch_size:
            message = await self.dequeue()
            if message:
                batch.append(message)
            else:
                break
        return batch

    async def mark_completed(self, message_id: str):
        """Marks message as successfully processed"""
        if message_id in self.messages:
            message = self.messages[message_id]
            message.processing_completed = datetime.now()

            # Calculate processing time
            processing_time = (
                message.processing_completed - message.processing_started
            ).total_seconds()

            # Update stats
            self.stats.update_processing_time(processing_time)
            self.stats.total_processed += 1

            # Update state
            self._update_message_state(message_id, MessageState.COMPLETED)

    async def mark_failed(self, message_id: str, error: str):
        """Marks message as failed and handles retry logic"""
        if message_id in self.messages:
            message = self.messages[message_id]
            message.error = error

            if message.retries < self.max_retries:
                # Retry message
                message.retries += 1
                self._update_message_state(message_id, MessageState.RETRYING)

                # Re-queue with same priority
                await self.queues[message.priority].put(
                    (message.priority.value, message_id)
                )

                self.stats.total_retried += 1
            else:
                # Mark as permanently failed
                self._update_message_state(message_id, MessageState.FAILED)
                self.stats.total_failed += 1

    async def _cleanup_loop(self):
        """Background task for cleaning up completed/failed messages"""
        while True:
            try:
                current_time = datetime.now()

                # Clean up old completed messages
                completed_cutoff = current_time - timedelta(hours=1)
                for message_id, state in list(self.message_states.items()):
                    if state == MessageState.COMPLETED:
                        message = self.messages[message_id]
                        if message.processing_completed < completed_cutoff:
                            del self.messages[message_id]
                            del self.message_states[message_id]

                # Check for stuck messages
                processing_cutoff = current_time - timedelta(
                    seconds=self.processing_timeout
                )
                for message_id, state in list(self.message_states.items()):
                    if state == MessageState.PROCESSING:
                        message = self.messages[message_id]
                        if message.processing_started < processing_cutoff:
                            await self.mark_failed(
                                message_id,
                                "Processing timeout"
                            )

                await asyncio.sleep(60)  # Run cleanup every minute

            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {str(e)}")
                await asyncio.sleep(5)

    async def _monitoring_loop(self):
        """Background task for monitoring queue health"""
        while True:
            try:
                # Collect queue metrics
                metrics = {
                    'queue_lengths': {
                        priority.name: self.queues[priority].qsize()
                        for priority in MessagePriority
                    },
                    'states': {
                        state.name: count
                        for state, count in self.stats.states.items()
                    },
                    'processing_time': self.stats.get_average_processing_time(),
                    'total_processed': self.stats.total_processed,
                    'total_failed': self.stats.total_failed,
                    'total_retried': self.stats.total_retried
                }

                # Log metrics
                self.logger.info(f"Queue metrics: {json.dumps(metrics)}")

                # Check for queue health issues
                self._check_queue_health(metrics)

                await asyncio.sleep(30)  # Run monitoring every 30 seconds

            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(5)

    def _update_message_state(self, message_id: str, new_state: MessageState):
        """Updates message state and statistics"""
        if message_id in self.message_states:
            old_state = self.message_states[message_id]
            self.stats.states[old_state] -= 1

        self.message_states[message_id] = new_state
        self.stats.states[new_state] += 1

    def _check_queue_health(self, metrics: Dict):
        """Checks queue health and logs warnings"""
        # Check queue sizes
        for priority, size in metrics['queue_lengths'].items():
            if size > self.max_size * 0.8:
                self.logger.warning(
                    f"Queue {priority} near capacity: {size}/{self.max_size}"
                )

        # Check processing times
        if metrics['processing_time'] > self.processing_timeout * 0.8:
            self.logger.warning(
                f"High average processing time: {metrics['processing_time']}s"
            )

        # Check failure rates
        failure_rate = (
            metrics['total_failed'] /
            (metrics['total_processed'] + metrics['total_failed'])
            if (metrics['total_processed'] + metrics['total_failed']) > 0
            else 0
        )

        if failure_rate > 0.1:  # More than 10% failures
            self.logger.warning(f"High failure rate: {failure_rate:.2%}")