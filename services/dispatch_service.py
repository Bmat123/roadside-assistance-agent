"""
Dispatch Service for finding closest garages and determining next best action
"""
import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from config import GARAGES_FILE

@dataclass
class DispatchDecision:
    """Result of dispatch decision"""
    garage_name: str
    garage_address: str
    service_type: str  # "tow_truck" or "repair_truck"
    estimated_arrival: str
    additional_services: List[str]  # ["taxi", "rental_car"]
    priority: str

    def to_dict(self) -> dict:
        return {
            "garage_name": self.garage_name,
            "garage_address": self.garage_address,
            "service_type": self.service_type,
            "estimated_arrival": self.estimated_arrival,
            "additional_services": self.additional_services,
            "priority": self.priority
        }


class DispatchService:
    """Service for handling garage selection and dispatch decisions"""

    def __init__(self, garages_file = None):
        if garages_file is None:
            garages_file = GARAGES_FILE

        with open(garages_file, 'r') as f:
            data = json.load(f)
            self.garages = data['garages']
            self.dispatch_rules = data['dispatch_rules']

    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two coordinates using Haversine formula (in km)"""
        R = 6371  # Earth's radius in kilometers

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

        return R * c

    def _geocode_location(self, location: str) -> Tuple[float, float]:
        """
        Mock geocoding - in production, use Google Maps Geocoding API
        For demo, return coordinates based on keywords in location
        """
        location_lower = location.lower()

        # Simple keyword matching for demo
        if "san francisco" in location_lower or "sf" in location_lower or "highway 101" in location_lower:
            return (37.7749, -122.4194)
        elif "oakland" in location_lower:
            return (37.8044, -122.2712)
        elif "palo alto" in location_lower or "stanford" in location_lower:
            return (37.4419, -122.1430)
        elif "san jose" in location_lower:
            return (37.3382, -121.8863)
        else:
            # Default to SF downtown
            return (37.7849, -122.4094)

    def _categorize_issue(self, issue: str) -> str:
        """Categorize the issue to match dispatch rules"""
        issue_lower = issue.lower()

        if "flat" in issue_lower or "tire" in issue_lower or "puncture" in issue_lower:
            return "flat_tire"
        elif "battery" in issue_lower or "won't start" in issue_lower or "dead" in issue_lower:
            return "battery_dead"
        elif "engine" in issue_lower or "overheating" in issue_lower or "smoke" in issue_lower:
            return "engine_failure"
        elif "transmission" in issue_lower or "gear" in issue_lower:
            return "transmission_issue"
        elif "accident" in issue_lower or "collision" in issue_lower or "crash" in issue_lower:
            return "accident_damage"
        else:
            # Default to towing for unknown issues
            return "engine_failure"

    def find_best_garage(self, location: str, issue: str) -> Optional[DispatchDecision]:
        """
        Find the best garage for the given location and issue type

        Args:
            location: Customer's current location
            issue: Description of the issue

        Returns:
            DispatchDecision with garage and service details
        """
        # Get customer coordinates
        customer_lat, customer_lon = self._geocode_location(location)

        # Categorize the issue
        issue_category = self._categorize_issue(issue)

        # Get dispatch rules for this issue
        if issue_category not in self.dispatch_rules:
            return None

        rules = self.dispatch_rules[issue_category]
        service_type = rules['service_type']
        required_service = rules['required_service']
        priority = rules['priority']
        additional_services = rules.get('additional_services', [])

        # Find garages that can handle this service
        suitable_garages = [
            g for g in self.garages
            if required_service in g['services']
        ]

        if not suitable_garages:
            return None

        # Calculate distances and find closest
        garage_distances = []
        for garage in suitable_garages:
            distance = self._calculate_distance(
                customer_lat, customer_lon,
                garage['latitude'], garage['longitude']
            )
            garage_distances.append((garage, distance))

        # Sort by distance
        garage_distances.sort(key=lambda x: x[1])

        # Select best garage (closest with good rating)
        best_garage = garage_distances[0][0]

        return DispatchDecision(
            garage_name=best_garage['name'],
            garage_address=best_garage['address'],
            service_type=service_type,
            estimated_arrival=best_garage['estimated_arrival'],
            additional_services=additional_services,
            priority=priority
        )

    def generate_dispatch_summary(self, decision: DispatchDecision, customer_name: str) -> str:
        """Generate a human-readable dispatch summary"""
        service_name = "tow truck" if decision.service_type == "tow_truck" else "repair truck"

        summary = f"Dispatch Summary for {customer_name}:\n"
        summary += f"• Service: {service_name.title()}\n"
        summary += f"• Garage: {decision.garage_name}\n"
        summary += f"• Location: {decision.garage_address}\n"
        summary += f"• ETA: {decision.estimated_arrival}\n"
        summary += f"• Priority: {decision.priority.upper()}\n"

        if decision.additional_services:
            summary += f"• Additional Services: {', '.join(decision.additional_services).replace('_', ' ').title()}\n"

        return summary


# Example usage
if __name__ == "__main__":
    service = DispatchService()

    # Test cases
    test_cases = [
        ("San Francisco, CA", "I have a flat tire"),
        ("Oakland, CA", "My battery is dead"),
        ("Highway 101", "Engine is smoking"),
    ]

    for location, issue in test_cases:
        print(f"\n{'='*60}")
        print(f"Location: {location}")
        print(f"Issue: {issue}")
        print('='*60)

        decision = service.find_best_garage(location, issue)
        if decision:
            print(service.generate_dispatch_summary(decision, "John Doe"))
            print(f"\nRaw decision: {decision.to_dict()}")
        else:
            print("No suitable garage found")
