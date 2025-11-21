"""
Event Processor: Main entry point
Correlates Kafka messages into experiment events and generates CSV
"""

import csv
import json
import logging
import sys
from pathlib import Path
from typing import List
from event_correlator import EventCorrelator
from event_definitions import Event

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
LOGGER = logging.getLogger(__name__)


class EventProcessor:
    """Processes collected Kafka messages and generates event CSV"""

    def __init__(self, collector_output_dir: Path, output_csv_path: Path):
        """
        Initialize processor.
        
        Args:
            collector_output_dir: Directory with JSONL files from KafkaCollector
            output_csv_path: Where to write the CSV file
        """
        self.collector_output_dir = Path(collector_output_dir)
        self.output_csv_path = Path(output_csv_path)
        self.correlator = EventCorrelator(self.collector_output_dir)

    def process(self) -> List[Event]:
        """Process and return solved events"""
        LOGGER.info("Processing events...")
        
        # Correlate all events
        events = self.correlator.correlate_events()
        
        LOGGER.info(f"Total solved events: {len(events)}")
        
        return events

    def generate_csv(self, events: List[Event], limit: int = 100):
        """
        Generate CSV file with events.
        
        Args:
            events: List of solved events
            limit: Maximum number of events to write (default 100)
        """
        LOGGER.info(f"Generating CSV with up to {limit} events: {self.output_csv_path}")
        
        # Limit to requested number
        events_to_write = events[:limit]
        
        if len(events_to_write) < limit:
            LOGGER.warning(f"Only {len(events_to_write)} events found, less than requested {limit}")
        
        try:
            with open(self.output_csv_path, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header
                writer.writerow(Event.csv_header())
                
                # Write events
                for event in events_to_write:
                    writer.writerow(event.to_csv_row())
            
            LOGGER.info(f"CSV written: {len(events_to_write)} events to {self.output_csv_path}")
            
        except Exception as e:
            LOGGER.error(f"Error writing CSV: {e}")
            raise

    @staticmethod
    def get_summary(events: List[Event]) -> dict:
        """Generate summary statistics"""
        if not events:
            return {
                "total_events": 0,
                "by_type": {},
                "avg_response_time_ms": None,
                "min_response_time_ms": None,
                "max_response_time_ms": None
            }
        
        by_type = {}
        response_times = []
        
        for event in events:
            event_type = event.event_type
            if event_type not in by_type:
                by_type[event_type] = 0
            by_type[event_type] += 1
            
            if event.total_response_time_ms:
                response_times.append(event.total_response_time_ms)
        
        avg_response = sum(response_times) / len(response_times) if response_times else None
        min_response = min(response_times) if response_times else None
        max_response = max(response_times) if response_times else None
        
        return {
            "total_events": len(events),
            "by_type": by_type,
            "avg_response_time_ms": avg_response,
            "min_response_time_ms": min_response,
            "max_response_time_ms": max_response
        }


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Process collected Kafka messages and generate event CSV"
    )
    parser.add_argument(
        '--collector-output',
        type=str,
        default='./collector_output',
        help='Directory with JSONL files from KafkaCollector (default: ./collector_output)'
    )
    parser.add_argument(
        '--output-csv',
        type=str,
        default='./events.csv',
        help='Output CSV file path (default: ./events.csv)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=100,
        help='Maximum events to write to CSV (default: 100)'
    )
    parser.add_argument(
        '--summary',
        action='store_true',
        help='Print summary statistics'
    )
    
    args = parser.parse_args()
    
    collector_output = Path(args.collector_output)
    output_csv = Path(args.output_csv)
    
    # Validate collector output exists
    if not collector_output.exists():
        LOGGER.error(f"Collector output directory not found: {collector_output}")
        sys.exit(1)
    
    # Ensure output directory exists
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Process events
        processor = EventProcessor(collector_output, output_csv)
        events = processor.process()
        
        # Generate CSV
        processor.generate_csv(events, limit=args.limit)
        
        # Print summary if requested
        if args.summary:
            summary = EventProcessor.get_summary(events)
            LOGGER.info(f"Summary: {json.dumps(summary, indent=2)}")
        
        LOGGER.info("Event processing complete!")
        sys.exit(0)
        
    except Exception as e:
        LOGGER.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()