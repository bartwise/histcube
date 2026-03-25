import ollama
import json
from datamodels.database import Neo4jDatabase
from datamodels.histcube import HistoricalLocation
from pydantic import BaseModel, Field
from shapely.geometry import Polygon, Point, LineString
from shapely import to_geojson
from langgraph.graph import StateGraph, START, END

from typing import List, Optional, Any


class Period(BaseModel):
    name: str = Field(..., description="Name of the historical period (e.g., 'Renaissance', '19th Century')")
    start_year: Optional[int] = Field(None, description="Start year of the period")
    end_year: Optional[int] = Field(None, description="End year of the period")

class LocationCoordinates(BaseModel):
    latitude: str|float = Field(..., description="Latitude of the location")
    longitude: str|float = Field(..., description="Longitude of the location")

class LocationPolygon(BaseModel):
    coordinates : List[LocationCoordinates] = Field([], description="List of coordinates defining the location (e.g., for a polygon)")

    def to_geojson(self) -> Polygon:
        points = [(coord.latitude, coord.longitude) for coord in self.coordinates]
        if len(points) == 0:
            return None
        elif len(points) == 1:
            return to_geojson(Point(points[0]))
        elif len(points) == 2:
            return to_geojson(LineString(points))
        return to_geojson(Polygon(points))

class Location(BaseModel):
    name: str = Field(..., description="Name of the location (e.g., 'France', 'Europe', 'Paris')")
    periods: list[str] = Field(..., description="Important historical periods for this location")
    sites: list[str] = Field(None, description="Famous sites for location")

class LocationExtended(Location):
    periods: list[Period]
    geojson: Any | None = None

class Locations(BaseModel):
    locations: list[Location] = Field([], description="List of historical locations, periods and sites")

class TaxonomyState(BaseModel):
    locations: list[Location] | None = None


class TaxonomyAgent:

    def __init__(self):
        self.agent = self.build_agent()

    def build_agent(self):
        workflow = StateGraph(TaxonomyState)
        workflow.add_node("collect_historical_locations", self.collect_historical_locations)
        workflow.add_node("enrich_locations", self.enrich_locations)
        workflow.add_node("store_data", self.store_data)

        workflow.add_edge(START, "collect_historical_locations")
        workflow.add_edge("collect_historical_locations", "enrich_locations")
        workflow.add_edge("enrich_locations", "store_data")
        workflow.add_edge("store_data", END)

        agent = workflow.compile()
        return agent

    def collect_historical_locations(self, state:TaxonomyState) -> TaxonomyState:
        json_schema = Locations.model_json_schema()
        prompt_template = f"""You are a historian and explorer. 
        Your task is to collect historical locations and periods.
        Return ONLY JSON. No explanations, no markdown.
        DO NOT repeat the json schema in your response, just return the data.
        Fieldnames in json response must match the following schema and be in lowercase.
        Return response in the following JSON schema:
        {json_schema}
        """

        response = ollama.chat("mistral", [{"role": "user", "content": prompt_template}], options={"temperature": 0.7})
        try:
            response_json = json.loads(response["message"]["content"])
            response_json = {k.lower(): v for k, v in response_json.items()}
            locations = Locations(**response_json)
            state.locations = locations.locations
        except Exception as e:
            raise ValueError(f"Failed to parse response as JSON: {response['message']['content']}")

        return state

    def enrich_locations(self, state:TaxonomyState) -> TaxonomyState:
        enrichted_locations = [
            self.extend_location_with_geojson(location) 
            for location in state.locations
        ]
        state.locations = enrichted_locations
        return state

    def store_data(self, state:TaxonomyState) -> TaxonomyState:
        Neo4jDatabase.init_driver()
        for location in state.locations:
            historical_location = HistoricalLocation.create(
                name=location.name, 
                geojson=location.geojson
            )
        Neo4jDatabase.close_driver()
        return state

    def enrich_periods(self, state:TaxonomyState) -> TaxonomyState:

        return state

    def extend_location_with_geojson(self, location:Location) -> LocationExtended:
        json_schema = LocationPolygon.model_json_schema()
        prompt_template = f"""You are a historian and explorer. 
        Your task is to get the coordinates for the location: {location.name}.
        Return ONLY JSON. No explanations, no markdown.
        DO NOT repeat the json schema in your response, just return the data.
        Fieldnames in json response must match the following schema and be in lowercase.
        Return response in the following JSON schema:
        {json_schema}
        """
        response = ollama.chat("mistral", [{"role": "user", "content": prompt_template}], options={"temperature": 0.7})
        try:
            response_json = json.loads(response["message"]["content"])
            response_json = {k.lower(): v for k, v in response_json.items()}
            location_polygon = LocationPolygon(**response_json)
        except Exception as e:
            raise ValueError(f"Failed to parse response as JSON: {response['message']['content']}")

        for coordinates in location_polygon.coordinates:
            coordinates.latitude = float(coordinates.latitude)
            coordinates.longitude = float(coordinates.longitude)
        geojson = location_polygon.to_geojson()

        return LocationExtended(
            name=location.name, 
            periods= [Period(name=period) for period in location.periods],
            geojson=geojson
        )
    
    def run(self):
        state = TaxonomyState()
        state = self.agent.invoke(state)
        return state