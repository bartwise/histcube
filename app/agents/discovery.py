import ollama
import json
from pydantic import BaseModel, Field

class DiscoveryInput(BaseModel):
    location: str = Field(..., description="The country, city, or region to explore")
    period: str = Field(..., description="The time period to explore, e.g. 'ancient', 'medieval', 'modern', or a specific century or year")
    latitude: str = Field(..., description="The latitude of the location to explore")
    longitude: str = Field(..., description="The longitude of the location to explore")

class DiscoveryAgent:

    """
    1. choose location and time to explore
    2. ask llm to generate a list of 5 interesting things to discover in that location and time
    3. for each thing, ask llm to generate a list of 5 questions to ask about that thing
    4. for each question, ask llm to generate a list of 5 facts that would answer that question
    5. store all the facts in the database, linked to the thing and question they answer
    """

    def __init__(self):
        pass

    def choose_input(self) -> DiscoveryInput:
        json_schema = DiscoveryInput.model_json_schema()

        prompt_template = f"""You are a historian and explorer. 
        Choose a location and time period to explore.
        Return ONLY JSON. No explanations, no markdown.
        Fieldnames in json response must match the following schema and be in lowercase.
        Return response in the following JSON schema:
        {json_schema}
        """

        response = ollama.chat("mistral", [{"role": "user", "content": prompt_template}], options={"temperature": 0.7})
        try:
            response_json = json.loads(response["message"]["content"])
            response_json = {k.lower(): v for k, v in response_json.items()}  # ensure keys are lowercase
            discover_input = DiscoveryInput(**response_json)
        except Exception as e:
            raise ValueError(f"Failed to parse response as JSON: {response['message']['content']}")


        return discover_input