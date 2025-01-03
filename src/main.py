from v2i_network import V2INetwork, Vehicle, RoadSideUnit
from message_handler import MessageProcessor, SecurityValidator
from detector import IntrusionDetector
from analyzer import DataAnalyzer
from transformer_model import EnhancedV2ITransformer, TransformerConfig
from message_queue import PriorityMessageQueue
from api_gateway import ApiGateway

import asyncio
import logging
from typing import Dict, List
import datetime
import json
import matplotlib.pyplot as plt
import seaborn as sns

class V2ISecuritySystem:
    """Main class integrating all system components"""
    def __init__(self, config_path: str):
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize components
        self.network = V2INetwork()
        self.message_queue = PriorityMessageQueue()
        self.message_processor = MessageProcessor()
        self.detector = IntrusionDetector()
        self.analyzer = DataAnalyzer()
        self.transformer = EnhancedV2ITransformer(
            TransformerConfig(**self.config['transformer'])
        )
        
        # Initialize API Gateway
        self.api_gateway = ApiGateway(
            self.detector,
            self.analyzer,
            self.transformer,
            self.config
        )
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Experiment metrics
        self.metrics = {
            'detection_rates': [],
            'false_positives': [],
            'false_negatives': [],
            'processing_times': [],
            'attack_detection_by_type': {}
        }

async def run_experiment(self):
        """Runs the complete experimental evaluation"""
        self.logger.info("Starting V2I security system experiment")
        
        # Setup network
        await self._setup_experimental_network()
        
        # Start system components
        await self._start_components()
        
        try:
            # Run different experimental scenarios
            await self._run_normal_traffic_scenario()
            await self._run_attack_scenarios()
            await self._run_mixed_scenario()
            
            # Analyze results
            self._analyze_results()
            
            # Generate visualizations
            self._generate_visualizations()
            
        finally:
            # Cleanup
            await self._stop_components()
            
    async def _setup_experimental_network(self):
        """Sets up network topology for experiment"""
        # Create RSUs
        for i in range(self.config['experiment']['n_rsus']):
            rsu = RoadSideUnit(
                node_id=f"RSU_{i}",
                position=self._generate_rsu_position(i),
                coverage_radius=self.config['experiment']['rsu_radius']
            )
            self.network.add_rsu(rsu)
            
        # Create legitimate vehicles
        for i in range(self.config['experiment']['n_vehicles']):
            vehicle = Vehicle(
                node_id=f"VEH_{i}",
                position=self._generate_vehicle_position()
            )
            self.network.add_vehicle(vehicle)
            
        self.logger.info(f"Network setup complete: "
                        f"{len(self.network.rsus)} RSUs, "
                        f"{len(self.network.vehicles)} vehicles")

    async def _run_normal_traffic_scenario(self):
        """Runs scenario with normal traffic patterns"""
        self.logger.info("Starting normal traffic scenario")
        
        duration = self.config['experiment']['normal_scenario_duration']
        start_time = datetime.datetime.now()
        
        while (datetime.datetime.now() - start_time).seconds < duration:
            # Generate normal traffic
            messages = self._generate_normal_traffic()
            
            # Process messages
            for msg in messages:
                await self.message_queue.enqueue(msg, MessagePriority.NORMAL)
                
            await asyncio.sleep(1)
            
        self.logger.info("Normal traffic scenario completed")

    async def _run_attack_scenarios(self):
        """Runs different attack scenarios"""
        attack_types = [
            'position_spoofing',
            'sybil_attack',
            'dos_attack',
            'replay_attack',
            'data_injection'
        ]
        
        for attack_type in attack_types:
            self.logger.info(f"Starting {attack_type} scenario")
            
            # Configure attack
            attack_config = self.config['experiment']['attacks'][attack_type]
            
            # Create attacker
            attacker = MaliciousVehicle(
                node_id=f"ATTACKER_{attack_type}",
                position=self._generate_vehicle_position(),
                attack_type=attack_type
            )
            
            # Run attack scenario
            await self._run_attack_scenario(attacker, attack_config)
            
            self.logger.info(f"Completed {attack_type} scenario")

    def _analyze_results(self):
        """Analyzes experimental results"""
        results = {
            'overall_detection_rate': np.mean(self.metrics['detection_rates']),
            'false_positive_rate': np.mean(self.metrics['false_positives']),
            'false_negative_rate': np.mean(self.metrics['false_negatives']),
            'avg_processing_time': np.mean(self.metrics['processing_times']),
            'attack_detection_rates': {
                attack_type: np.mean(rates)
                for attack_type, rates in 
                self.metrics['attack_detection_by_type'].items()
            }
        }
        
        self.logger.info(f"Experiment results: {json.dumps(results, indent=2)}")
        return results

    def _generate_visualizations(self):
        """Generates visualization of results"""
        # Detection rates by attack type
        plt.figure(figsize=(12, 6))
        attack_types = list(self.metrics['attack_detection_by_type'].keys())
        detection_rates = [
            np.mean(self.metrics['attack_detection_by_type'][at])
            for at in attack_types
        ]
        
        sns.barplot(x=attack_types, y=detection_rates)
        plt.title('Detection Rates by Attack Type')
        plt.ylabel('Detection Rate')
        plt.xlabel('Attack Type')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig('detection_rates.png')
        
        # Processing times
        plt.figure(figsize=(12, 6))
        sns.histplot(self.metrics['processing_times'])
        plt.title('Message Processing Times')
        plt.xlabel('Processing Time (ms)')
        plt.ylabel('Count')
        plt.tight_layout()
        plt.savefig('processing_times.png')

async def main():
    # Load system configuration
    config_path = "config/system_config.json"
    
    # Initialize system
    system = V2ISecuritySystem(config_path)
    
    # Run experiment
    await system.run_experiment()
    
if __name__ == "__main__":
    asyncio.run(main())