"""
Roadside Assistance Agent using Google Gemini AI with Structured Outputs
"""
import json
import google.generativeai as genai
from dotenv import load_dotenv
from pathlib import Path
import sys
from typing import Optional

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from config import (
    API_KEY, MODEL_NAME, POLICY_COVERAGE_FILE,
    SYSTEM_INSTRUCTION_FILE, CUSTOMERS_FILE
)
from services.dispatch_service import DispatchService

load_dotenv()

class RoadsideAgent:
    def __init__(self):
        # Configure API
        if not API_KEY:
            print("⚠️ WARNING: GOOGLE_API_KEY not found. The agent will fail.")

        genai.configure(api_key=API_KEY)

        # Initialize dispatch service
        self.dispatch_service = DispatchService()

        # Load policy document
        try:
            with open(POLICY_COVERAGE_FILE, 'r') as f:
                policy_doc = json.load(f)
            policy_text = json.dumps(policy_doc, indent=2)
        except FileNotFoundError:
            print(f"⚠️ WARNING: {POLICY_COVERAGE_FILE} not found. Coverage check will fail.")
            policy_text = "{}"

        # Load customer database
        try:
            with open(CUSTOMERS_FILE, 'r') as f:
                customer_list = json.load(f)
            customer_text = json.dumps(customer_list, indent=2)
        except FileNotFoundError:
            print(f"⚠️ WARNING: {CUSTOMERS_FILE} not found. All customers will default to basic policy.")
            customer_text = "[]"

        # Load system instruction template
        try:
            with open(SYSTEM_INSTRUCTION_FILE, 'r') as f:
                system_instruction_template = f.read()
        except FileNotFoundError:
            print(f"⚠️ WARNING: {SYSTEM_INSTRUCTION_FILE} not found. Using default prompt.")
            system_instruction_template = "You are a helpful assistant. {policy_text} {customer_text}"

        # Inject policy and customer database into system instruction
        system_instruction = system_instruction_template.format(
            policy_text=policy_text,
            customer_text=customer_text
        )

        # Define the response schema for structured output
        response_schema = {
            "type": "object",
            "properties": {
                "voice_response": {
                    "type": "string",
                    "description": "The text to speak to the customer"
                },
                "is_covered": {
                    "type": "boolean",
                    "description": "Whether the issue is covered (false until all data collected and checked)"
                },
                "conversation_complete": {
                    "type": "boolean",
                    "description": "Set to true only when the customer confirms they need nothing else and the conversation is fully closed"
                },
                "collected_data": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Customer's name or empty string if not collected yet"
                        },
                        "car": {
                            "type": "string",
                            "description": "Vehicle model or empty string if not collected yet"
                        },
                        "location": {
                            "type": "string",
                            "description": "Current location or empty string if not collected yet"
                        },
                        "issue": {
                            "type": "string",
                            "description": "Description of the issue or empty string if not collected yet"
                        },
                        "policy_level": {
                            "type": "string",
                            "description": "Customer's policy level (basic/premium/platinum) looked up by name, or empty string if name not yet collected"
                        }
                    },
                    "required": ["name", "car", "location", "issue", "policy_level"]
                }
            },
            "required": ["voice_response", "is_covered", "conversation_complete", "collected_data"]
        }

        # Create the GenerativeModel with structured output
        self.model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            system_instruction=system_instruction,
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": response_schema
            }
        )

    def process_request(self, history, user_text):
        """
        Sends the user text to Gemini with the conversation history.
        Returns the parsed JSON response with dispatch information if covered.
        Uses Gemini's native structured output (JSON mode).
        """
        try:
            # Start a chat session with the provided history
            chat = self.model.start_chat(history=history)

            # Send the message - Gemini will return valid JSON matching our schema
            response = chat.send_message(user_text)

            # Parse the JSON response (guaranteed to be valid JSON)
            result = json.loads(response.text)

            # If covered, add dispatch information
            if result.get("is_covered") and result.get("collected_data"):
                collected = result["collected_data"]
                location = collected.get("location", "")
                issue = collected.get("issue", "")
                name = collected.get("name", "Customer")

                # Check if we have actual data (not empty strings)
                if location and issue and location.strip() and issue.strip():
                    # Find best garage and create dispatch decision
                    dispatch_decision = self.dispatch_service.find_best_garage(location, issue)

                    if dispatch_decision:
                        # Generate detailed dispatch message
                        dispatch_summary = self.dispatch_service.generate_dispatch_summary(
                            dispatch_decision, name
                        )

                        # Update UI with dispatch details
                        result["ui_update"] = {
                            "type": "SMS_NOTIFICATION",
                            "content": f"Help is on the way!\n\n{dispatch_summary}",
                            "status": "DISPATCHED"
                        }

                        # Add dispatch details to result
                        result["dispatch_details"] = dispatch_decision.to_dict()

                        # Enhance voice response with dispatch info
                        service_type = "tow truck" if dispatch_decision.service_type == "tow_truck" else "repair truck"
                        result["voice_response"] += f" A {service_type} from {dispatch_decision.garage_name} will arrive in approximately {dispatch_decision.estimated_arrival}."
                else:
                    # Not all data collected yet
                    result["ui_update"] = None
                    result["dispatch_details"] = None
            else:
                # Not covered or data incomplete
                result["ui_update"] = None
                result["dispatch_details"] = None

            return result

        except json.JSONDecodeError as e:
            print(f"❌ JSON DECODE ERROR: {e}")
            print(f"    Raw response: {response.text if 'response' in locals() else 'N/A'}")
            return {
                "voice_response": "I apologize, I had trouble processing that. Could you please repeat?",
                "ui_update": None,
                "collected_data": {"name": "", "car": "", "location": "", "issue": "", "policy_level": ""},
                "is_covered": False
            }
        except Exception as e:
            print(f"❌ AGENT ERROR: {e}")
            import traceback
            traceback.print_exc()
            return {
                "voice_response": "I am having trouble connecting to the AI service. Please check the server logs.",
                "ui_update": None,
                "collected_data": {"name": "", "car": "", "location": "", "issue": "", "policy_level": ""},
                "is_covered": False
            }
