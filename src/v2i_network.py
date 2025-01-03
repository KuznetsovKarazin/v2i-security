import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
import datetime
from enum import Enum
import random

@dataclass
class Position:
    """Represents geographical position of a network node"""
    latitude: float
    longitude: float
    timestamp: datetime.datetime

@dataclass
class NetworkNode:
    """Base class for all network participants"""
    node_id: str
    position: Position
    node_type: str
    trust_score: float = 1.0

class Vehicle(NetworkNode):
    """Represents a vehicle in V2I network"""
    def __init__(self, node_id: str, position: Position):
        super().__init__(node_id, position, "vehicle")
        self.speed: float = 0.0
        self.direction: float = 0.0
        self.movement_history: List[Position] = []

    def update_position(self, new_position: Position) -> None:
        """Updates vehicle position and maintains movement history"""
        self.movement_history.append(self.position)
        self.position = new_position
        if len(self.movement_history) > 100:  # Keep last 100 positions
            self.movement_history.pop(0)

class RoadSideUnit(NetworkNode):
    """Represents infrastructure node (RSU) in V2I network"""
    def __init__(self, node_id: str, position: Position, coverage_radius: float):
        super().__init__(node_id, position, "rsu")
        self.coverage_radius = coverage_radius
        self.connected_vehicles: Dict[str, Vehicle] = {}

    def is_in_range(self, vehicle: Vehicle) -> bool:
        """Checks if vehicle is within RSU coverage area"""
        distance = self._calculate_distance(vehicle.position)
        return distance <= self.coverage_radius

    def _calculate_distance(self, pos: Position) -> float:
        """Calculates distance between RSU and given position"""
        return np.sqrt(
            (pos.latitude - self.position.latitude) ** 2 +
            (pos.longitude - self.position.longitude) ** 2
        )

class V2INetwork:
    """Main class for V2I network simulation"""
    def __init__(self):
        self.vehicles: Dict[str, Vehicle] = {}
        self.rsus: Dict[str, RoadSideUnit] = {}
        self.network_time: datetime.datetime = datetime.datetime.now()

    def add_vehicle(self, vehicle: Vehicle) -> None:
        """Registers new vehicle in the network"""
        self.vehicles[vehicle.node_id] = vehicle
        self._update_connections(vehicle)

    def add_rsu(self, rsu: RoadSideUnit) -> None:
        """Registers new RSU in the network"""
        self.rsus[rsu.node_id] = rsu

    def update_vehicle_position(self, vehicle_id: str,
                              new_position: Position) -> None:
        """Updates vehicle position and maintains network connections"""
        if vehicle_id in self.vehicles:
            self.vehicles[vehicle_id].update_position(new_position)
            self._update_connections(self.vehicles[vehicle_id])

    def _update_connections(self, vehicle: Vehicle) -> None:
        """Updates vehicle-RSU connections based on position"""
        for rsu in self.rsus.values():
            if rsu.is_in_range(vehicle):
                rsu.connected_vehicles[vehicle.node_id] = vehicle
            elif vehicle.node_id in rsu.connected_vehicles:
                del rsu.connected_vehicles[vehicle.node_id]

    def get_network_state(self) -> Dict:
        """Returns current state of the network"""
        return {
            'timestamp': self.network_time,
            'vehicle_count': len(self.vehicles),
            'rsu_count': len(self.rsus),
            'connections': self._get_connection_stats()
        }

    def _get_connection_stats(self) -> Dict:
        """Calculates network connection statistics"""
        total_connections = sum(
            len(rsu.connected_vehicles) for rsu in self.rsus.values()
        )
        return {
            'total_connections': total_connections,
            'average_per_rsu': total_connections / len(self.rsus)
                if self.rsus else 0
        }

class AttackType(Enum):
    """Extended types of possible attacks in V2I network"""
    POSITION_SPOOFING = "position_spoofing"
    SYBIL = "sybil_attack"
    DOS = "denial_of_service"
    REPLAY = "replay_attack"
    DATA_INJECTION = "data_injection"
    # New attack types
    TIMING_ATTACK = "timing_attack"
    BLACK_HOLE = "black_hole_attack"
    GHOST_VEHICLE = "ghost_vehicle_attack"
    RSU_IMPERSONATION = "rsu_impersonation"
    TRAJECTORY_SPOOFING = "trajectory_spoofing"

class MaliciousVehicle(Vehicle):
    """Represents an attacker in the network"""
    def __init__(self, node_id: str, position: Position, attack_type: AttackType):
        super().__init__(node_id, position)
        self.attack_type = attack_type
        self.attack_active = False
        self.original_position = position
        self.fake_identities: List[Vehicle] = []

    def launch_attack(self) -> Dict:
        """Initiates attack based on its type"""
        self.attack_active = True
        attack_data = {}

        if self.attack_type == AttackType.POSITION_SPOOFING:
            attack_data = self._execute_position_spoofing()
        elif self.attack_type == AttackType.SYBIL:
            attack_data = self._execute_sybil_attack()
        elif self.attack_type == AttackType.DOS:
            attack_data = self._execute_dos_attack()
        elif self.attack_type == AttackType.REPLAY:
            attack_data = self._execute_replay_attack()
        elif self.attack_type == AttackType.DATA_INJECTION:
            attack_data = self._execute_data_injection()

        return attack_data

    def _execute_position_spoofing(self) -> Dict:
        """Generates fake position data"""
        noise = np.random.normal(0, 0.001, 2)  # Small position perturbation
        fake_position = Position(
            latitude=self.position.latitude + noise[0],
            longitude=self.position.longitude + noise[1],
            timestamp=datetime.datetime.now()
        )
        self.position = fake_position
        return {
            'attack_type': AttackType.POSITION_SPOOFING,
            'original_position': self.original_position,
            'spoofed_position': fake_position
        }

    def _execute_sybil_attack(self) -> Dict:
        """Creates multiple fake vehicle identities"""
        num_fake_identities = random.randint(3, 7)
        self.fake_identities = []

        for i in range(num_fake_identities):
            noise = np.random.normal(0, 0.0005, 2)
            fake_position = Position(
                latitude=self.position.latitude + noise[0],
                longitude=self.position.longitude + noise[1],
                timestamp=datetime.datetime.now()
            )
            fake_vehicle = Vehicle(f"{self.node_id}_fake_{i}", fake_position)
            self.fake_identities.append(fake_vehicle)

        return {
            'attack_type': AttackType.SYBIL,
            'num_fake_identities': num_fake_identities,
            'fake_vehicles': self.fake_identities
        }

    def _execute_dos_attack(self) -> Dict:
        """Simulates DoS attack by generating high-volume traffic"""
        message_flood = [
            {'timestamp': datetime.datetime.now(), 'size': random.randint(1000, 5000)}
            for _ in range(1000)
        ]
        return {
            'attack_type': AttackType.DOS,
            'message_count': len(message_flood),
            'total_size': sum(m['size'] for m in message_flood)
        }

    def _execute_replay_attack(self) -> Dict:
        """Replays previously captured legitimate messages"""
        if not self.movement_history:
            return {'attack_type': AttackType.REPLAY, 'success': False}

        replayed_position = random.choice(self.movement_history)
        self.position = replayed_position
        return {
            'attack_type': AttackType.REPLAY,
            'replayed_position': replayed_position,
            'original_timestamp': replayed_position.timestamp
        }

    def _execute_data_injection(self) -> Dict:
        """Injects malicious data into the network"""
        fake_data = {
            'emergency': random.choice([True, False]),
            'speed': random.uniform(0, 200),
            'direction': random.uniform(0, 360)
        }
        return {
            'attack_type': AttackType.DATA_INJECTION,
            'injected_data': fake_data
        }

class AttackSimulator:
    """Manages attack simulation in the network"""
    def __init__(self, network: V2INetwork):
        self.network = network
        self.active_attackers: Dict[str, MaliciousVehicle] = {}
        self.attack_history: List[Dict] = []

    def add_attacker(self, attacker: MaliciousVehicle) -> None:
        """Registers new attacker in the network"""
        self.active_attackers[attacker.node_id] = attacker
        self.network.add_vehicle(attacker)

    def launch_attack(self) -> Dict:
        """Initiates attack based on its type"""
        self.attack_active = True
        attack_data = {}

        attack_methods = {
            AttackType.POSITION_SPOOFING: self._execute_position_spoofing,
            AttackType.SYBIL: self._execute_sybil_attack,
            AttackType.DOS: self._execute_dos_attack,
            AttackType.REPLAY: self._execute_replay_attack,
            AttackType.DATA_INJECTION: self._execute_data_injection,
            AttackType.TIMING_ATTACK: self._execute_timing_attack,
            AttackType.BLACK_HOLE: self._execute_black_hole_attack,
            AttackType.GHOST_VEHICLE: self._execute_ghost_vehicle_attack,
            AttackType.RSU_IMPERSONATION: self._execute_rsu_impersonation,
            AttackType.TRAJECTORY_SPOOFING: self._execute_trajectory_spoofing
        }

        if self.attack_type in attack_methods:
            attack_data = attack_methods[self.attack_type]()

        return attack_data

    def _execute_timing_attack(self) -> Dict:
        """
        Simulates timing attack by manipulating message timestamps
        to disrupt time-critical V2I operations
        """
        current_time = datetime.datetime.now()
        delay_patterns = [
            datetime.timedelta(milliseconds=random.randint(100, 500)),
            datetime.timedelta(seconds=-2),
            datetime.timedelta(seconds=5)
        ]

        manipulated_messages = []
        for _ in range(10):
            delay = random.choice(delay_patterns)
            fake_timestamp = current_time + delay
            manipulated_messages.append({
                'original_time': current_time,
                'manipulated_time': fake_timestamp,
                'delay': delay.total_seconds()
            })

        return {
            'attack_type': AttackType.TIMING_ATTACK,
            'message_count': len(manipulated_messages),
            'manipulated_timestamps': manipulated_messages
        }

    def _execute_black_hole_attack(self) -> Dict:
        """
        Simulates black hole attack where attacker drops all received messages
        instead of forwarding them
        """
        dropped_messages = []
        for _ in range(random.randint(20, 50)):
            dropped_message = {
                'timestamp': datetime.datetime.now(),
                'priority': random.choice(['high', 'medium', 'low']),
                'dropped': True
            }
            dropped_messages.append(dropped_message)

        return {
            'attack_type': AttackType.BLACK_HOLE,
            'dropped_count': len(dropped_messages),
            'dropped_messages': dropped_messages
        }

    def _execute_ghost_vehicle_attack(self) -> Dict:
        """
        Creates ghost vehicle that appears and disappears randomly
        to confuse traffic management systems
        """
        ghost_positions = []
        base_position = self.position

        for _ in range(5):
            # Generate random position jumps
            jump_distance = random.uniform(0.001, 0.005)
            jump_angle = random.uniform(0, 2 * np.pi)

            ghost_position = Position(
                latitude=base_position.latitude + jump_distance * np.cos(jump_angle),
                longitude=base_position.longitude + jump_distance * np.sin(jump_angle),
                timestamp=datetime.datetime.now()
            )
            ghost_positions.append(ghost_position)

        return {
            'attack_type': AttackType.GHOST_VEHICLE,
            'ghost_positions': ghost_positions,
            'appearance_pattern': 'random',
            'duration': random.randint(5, 15)  # seconds
        }

    def _execute_rsu_impersonation(self) -> Dict:
        """
        Simulates RSU impersonation by broadcasting fake infrastructure messages
        """
        fake_rsu_id = f"fake_rsu_{random.randint(1000, 9999)}"
        fake_messages = []

        message_types = [
            'traffic_signal_status',
            'weather_condition',
            'road_condition',
            'emergency_alert'
        ]

        for _ in range(random.randint(5, 15)):
            fake_message = {
                'rsu_id': fake_rsu_id,
                'message_type': random.choice(message_types),
                'content': self._generate_fake_rsu_content(),
                'timestamp': datetime.datetime.now()
            }
            fake_messages.append(fake_message)

        return {
            'attack_type': AttackType.RSU_IMPERSONATION,
            'fake_rsu_id': fake_rsu_id,
            'message_count': len(fake_messages),
            'fake_messages': fake_messages
        }

    def _execute_trajectory_spoofing(self) -> Dict:
        """
        Creates physically impossible vehicle trajectories
        to confuse trajectory prediction systems
        """
        original_trajectory = self.movement_history.copy()
        spoofed_trajectory = []
        current_position = self.position

        for _ in range(10):
            # Generate physically impossible movements
            if random.random() < 0.3:
                # Sudden teleportation
                jump_distance = random.uniform(0.01, 0.05)
                new_position = Position(
                    latitude=current_position.latitude + jump_distance,
                    longitude=current_position.longitude + jump_distance,
                    timestamp=datetime.datetime.now()
                )
            else:
                # Impossible acceleration/deceleration
                small_change = random.uniform(0.0001, 0.0005)
                new_position = Position(
                    latitude=current_position.latitude + small_change,
                    longitude=current_position.longitude + small_change,
                    timestamp=datetime.datetime.now()
                )

            spoofed_trajectory.append(new_position)
            current_position = new_position

        return {
            'attack_type': AttackType.TRAJECTORY_SPOOFING,
            'original_trajectory': original_trajectory,
            'spoofed_trajectory': spoofed_trajectory,
            'anomaly_points': self._detect_trajectory_anomalies(spoofed_trajectory)
        }

    def _generate_fake_rsu_content(self) -> Dict:
        """Helper method to generate fake RSU message content"""
        content_types = {
            'traffic_signal_status': lambda: {
                'signal_id': random.randint(1, 100),
                'state': random.choice(['red', 'yellow', 'green']),
                'duration': random.randint(10, 60)
            },
            'weather_condition': lambda: {
                'temperature': random.uniform(-10, 40),
                'precipitation': random.uniform(0, 100),
                'visibility': random.uniform(0, 1000)
            },
            'road_condition': lambda: {
                'surface_status': random.choice(['dry', 'wet', 'icy', 'snowy']),
                'maintenance_needed': random.choice([True, False])
            },
            'emergency_alert': lambda: {
                'alert_type': random.choice(['accident', 'roadwork', 'hazard']),
                'severity': random.choice(['low', 'medium', 'high']),
                'location_offset': random.uniform(-1000, 1000)
            }
        }

        content_type = random.choice(list(content_types.keys()))
        return content_types[content_type]()

    def _detect_trajectory_anomalies(self, trajectory: List[Position]) -> List[Dict]:
        """Identifies anomalous points in the spoofed trajectory"""
        anomalies = []

        for i in range(1, len(trajectory)):
            prev_pos = trajectory[i-1]
            curr_pos = trajectory[i]

            # Calculate speed between points
            time_diff = (curr_pos.timestamp - prev_pos.timestamp).total_seconds()
            distance = np.sqrt(
                (curr_pos.latitude - prev_pos.latitude)**2 +
                (curr_pos.longitude - prev_pos.longitude)**2
            )
            speed = distance / time_diff if time_diff > 0 else float('inf')

            # Check for anomalies
            if speed > 100:  # Unrealistic speed threshold
                anomalies.append({
                    'position_index': i,
                    'calculated_speed': speed,
                    'timestamp': curr_pos.timestamp
                })

        return anomalies

    def get_attack_statistics(self) -> Dict:
        """Returns statistics about conducted attacks"""
        attack_types = [record['attack_type'] for record in self.attack_history]
        return {
            'total_attacks': len(self.attack_history),
            'unique_attackers': len(set(record['attacker_id']
                                     for record in self.attack_history)),
            'attack_distribution': {
                attack_type: attack_types.count(attack_type)
                for attack_type in AttackType
            }
        }