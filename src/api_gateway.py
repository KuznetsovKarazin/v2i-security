from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional
from pydantic import BaseModel
import asyncio
from datetime import datetime
import jwt
from enum import Enum
import logging

# Data Models
class MessagePriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class V2IMessage(BaseModel):
    message_id: str
    sender_id: str
    message_type: str
    timestamp: datetime
    priority: MessagePriority
    content: Dict
    signature: Optional[str] = None

class DetectionResponse(BaseModel):
    status: str
    threat_detected: bool
    confidence: float
    threat_type: Optional[str]
    recommendations: List[str]
    timestamp: datetime

class SystemStatus(BaseModel):
    status: str
    active_nodes: int
    processed_messages: int
    detected_threats: int
    system_health: Dict
    last_update: datetime

class ApiGateway:
    """Main API Gateway for V2I Intrusion Detection System"""
    def __init__(self,
                 detector,
                 analyzer,
                 transformer_model,
                 config: Dict):
        self.app = FastAPI(title="V2I Intrusion Detection System API")
        self.detector = detector
        self.analyzer = analyzer
        self.transformer = transformer_model
        self.config = config

        # System state
        self.active_sessions: Dict[str, Dict] = {}
        self.message_queue = asyncio.Queue()
        self.system_metrics = SystemMetrics()

        # Setup logging
        self.logger = self._setup_logging()

        # Configure CORS
        self.setup_cors()

        # Initialize routes
        self.setup_routes()

        # Start background tasks
        self.background_tasks = BackgroundTasks()
        self.background_tasks.add_task(self.process_message_queue)

    def _setup_logging(self) -> logging.Logger:
        """Configures system logging"""
        logger = logging.getLogger("v2i_ids")
        logger.setLevel(logging.INFO)

        handler = logging.FileHandler("v2i_ids.log")
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def setup_cors(self):
        """Configures CORS settings"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def setup_routes(self):
        """Sets up API routes"""
        @self.app.post("/v2i/message", response_model=DetectionResponse)
        async def process_message(message: V2IMessage):
            return await self.handle_message(message)

        @self.app.get("/v2i/status", response_model=SystemStatus)
        async def get_system_status():
            return await self.get_status()

        @self.app.post("/v2i/batch", response_model=List[DetectionResponse])
        async def process_batch(messages: List[V2IMessage]):
            return await self.handle_batch(messages)

    async def handle_message(self, message: V2IMessage) -> DetectionResponse:
        """Handles incoming V2I messages"""
        try:
            # Validate message
            self._validate_message(message)

            # Add to processing queue
            await self.message_queue.put(message)

            # Process message
            detection_result = await self._process_single_message(message)

            # Update metrics
            self.system_metrics.update_message_processed()

            # Log result
            self.logger.info(
                f"Processed message {message.message_id} with result: {detection_result}"
            )

            return detection_result

        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def _process_single_message(self,
                                    message: V2IMessage) -> DetectionResponse:
        """Processes a single message through the detection pipeline"""
        # Initial detection
        detection_result = self.detector.process_message(message.dict())

        # Deep analysis if threat suspected
        if detection_result.confidence > self.config['analysis_threshold']:
            analysis_result = self.analyzer.analyze_detection(
                detection_result,
                message.dict()
            )

            # Transform sequence
            if analysis_result.anomaly_score > self.config['transform_threshold']:
                sequence = self._prepare_sequence(message.sender_id)
                transform_result = self.transformer.forward(sequence)

                # Combine results
                final_result = self._combine_results(
                    detection_result,
                    analysis_result,
                    transform_result
                )

                return self._create_response(final_result)

        return self._create_response(detection_result)

    async def process_message_queue(self):
        """Background task for processing message queue"""
        while True:
            try:
                # Process messages in batches
                messages = []
                try:
                    while len(messages) < self.config['batch_size']:
                        message = await asyncio.wait_for(
                            self.message_queue.get(),
                            timeout=self.config['batch_timeout']
                        )
                        messages.append(message)
                except asyncio.TimeoutError:
                    pass

                if messages:
                    # Process batch
                    await self._process_message_batch(messages)

            except Exception as e:
                self.logger.error(f"Error in message queue processing: {str(e)}")
                await asyncio.sleep(1)

    def _validate_message(self, message: V2IMessage):
        """Validates incoming message format and signature"""
        if message.signature:
            try:
                jwt.decode(
                    message.signature,
                    self.config['jwt_secret'],
                    algorithms=['HS256']
                )
            except jwt.InvalidTokenError:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid message signature"
                )

    def _prepare_sequence(self, sender_id: str) -> Dict:
        """Prepares message sequence for transformer model"""
        if sender_id not in self.active_sessions:
            self.active_sessions[sender_id] = {
                'messages': [],
                'last_update': datetime.now()
            }

        session = self.active_sessions[sender_id]

        # Maintain sequence length
        if len(session['messages']) > self.config['max_sequence_length']:
            session['messages'].pop(0)

        return {
            'messages': session['messages'],
            'metadata': {
                'sender_id': sender_id,
                'session_start': session['messages'][0]['timestamp']
                if session['messages'] else datetime.now()
            }
        }

    def _combine_results(self,
                        detection: DetectionResult,
                        analysis: AnalysisResult,
                        transform: Dict) -> Dict:
        """Combines results from different processing stages"""
        return {
            'threat_detected': detection.threat_detected or
                             analysis.anomaly_score > self.config['threat_threshold'],
            'confidence': max(detection.confidence, analysis.anomaly_score),
            'threat_type': detection.threat_type or analysis.anomaly_type,
            'evidence': {
                'detection': detection.evidence,
                'analysis': analysis.context_analysis,
                'transform': transform
            }
        }

    def _create_response(self, result: Dict) -> DetectionResponse:
        """Creates API response from processing result"""
        return DetectionResponse(
            status="success",
            threat_detected=result['threat_detected'],
            confidence=result['confidence'],
            threat_type=result['threat_type'],
            recommendations=self._generate_recommendations(result),
            timestamp=datetime.now()
        )

    def _generate_recommendations(self, result: Dict) -> List[str]:
        """Generates recommendations based on detection results"""
        recommendations = []

        if result['threat_detected']:
            threat_type = result['threat_type']
            confidence = result['confidence']

            if confidence > 0.9:
                recommendations.append("URGENT: Immediate action required")

            if threat_type in self.config['recommendation_templates']:
                recommendations.extend(
                    self.config['recommendation_templates'][threat_type]
                )

        return recommendations