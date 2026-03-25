from pydantic import BaseModel, Field
from datetime import date
from typing import Optional, Dict, Any, Type, TypeVar

from datamodels.database import session

T = TypeVar("T", bound="Neo4jModel")


class Neo4jModel(BaseModel):
    """Base helper for models that persist to Neo4j.
    Provides common helpers used by all concrete models.
    """

    node_id: Optional[int] = Field(None, description="Neo4j internal node id")

    class Config:
        orm_mode = True

    def _props(self) -> Dict[str, Any]:
        """Return a dictionary of properties to store on the node (excludes node_id)."""
        data = self.model_dump()
        data.pop("node_id", None)
        # Convert dates to ISO strings so Neo4j stores them as strings
        for k, v in list(data.items()):
            if isinstance(v, date):
                data[k] = v.isoformat()
        return data

    @classmethod
    def _label(cls) -> str:
        return cls.__name__

    @classmethod
    def create(cls: Type[T], **kwargs) -> T:
        """Create a node and return a model instance with `node_id` set."""
        instance = cls(**kwargs)
        props = instance._props()
        cypher = f"CREATE (n:{cls._label()} $props) RETURN id(n) AS node_id, n"
        with session() as s:
            result = s.run(cypher, props=props)
            record = result.single()
            if record is None:
                raise RuntimeError("Failed to create node")
            instance.node_id = record["node_id"]
        return instance

    @classmethod
    def get_by_node_id(cls: Type[T], node_id: int) -> Optional[T]:
        cypher = f"MATCH (n) WHERE id(n) = $node_id RETURN id(n) AS node_id, n LIMIT 1"
        with session() as s:
            result = s.run(cypher, node_id=node_id)
            record = result.single()
            if not record:
                return None
            props = dict(record["n"]) if "n" in record else {}
            # Convert moment strings back to date where appropriate
            if "moment" in props:
                try:
                    props["moment"] = date.fromisoformat(props["moment"])
                except Exception:
                    pass
            props["node_id"] = record["node_id"]
            return cls(**props)

    def save(self) -> "Neo4jModel":
        """Create or update the node in the database and return self with node_id set."""
        props = self._props()
        if self.node_id is None:
            created = self.create(**props)
            self.node_id = created.node_id
            return self
        # update existing node
        cypher = f"MATCH (n) WHERE id(n) = $node_id SET n += $props RETURN id(n) AS node_id, n"
        with session() as s:
            result = s.run(cypher, node_id=self.node_id, props=props)
            record = result.single()
            if not record:
                raise RuntimeError("Failed to update node")
        return self

    def delete(self) -> bool:
        """Delete this node from the database. Returns True if deleted."""
        if self.node_id is None:
            raise RuntimeError("node_id is required to delete")
        cypher = "MATCH (n) WHERE id(n) = $node_id DETACH DELETE n RETURN count(n) AS deleted"
        with session() as s:
            result = s.run(cypher, node_id=self.node_id)
            record = result.single()
            return bool(record and record.get("deleted", 0) > 0)


class HistCube(Neo4jModel):
    latitude: float = Field(..., description="Latitude of the location")
    longtitude: float = Field(..., description="Longitude of the location")
    moment: date = Field(..., description="Date in history")

    @classmethod
    def get_by_coords_and_moment(
        cls, latitude: float, longtitude: float, moment: date
    ) -> Optional["HistCube"]:
        cypher = (
            f"MATCH (n:{cls._label()}) "
            "WHERE n.latitude = $latitude AND n.longtitude = $longtitude AND n.moment = $moment "
            "RETURN id(n) AS node_id, n LIMIT 1"
        )
        with session() as s:
            result = s.run(
                cypher,
                latitude=latitude,
                longtitude=longtitude,
                moment=moment.isoformat(),
            )
            record = result.single()
            if not record:
                return None
            props = dict(record["n"]) if "n" in record else {}
            if "moment" in props:
                try:
                    props["moment"] = date.fromisoformat(props["moment"])
                except Exception:
                    pass
            props["node_id"] = record["node_id"]
            return cls(**props)


class Nation(Neo4jModel):
    name: str = Field(..., description="Name of the nation")
    description: str = Field(..., description="Description of the nation")

    @classmethod
    def get_by_name(cls, name: str) -> Optional["Nation"]:
        cypher = f"MATCH (n:{cls._label()} {{name: $name}}) RETURN id(n) AS node_id, n LIMIT 1"
        with session() as s:
            result = s.run(cypher, name=name)
            record = result.single()
            if not record:
                return None
            props = dict(record["n"]) if "n" in record else {}
            props["node_id"] = record["node_id"]
            return cls(**props)


class Person(Neo4jModel):
    name: str = Field(..., description="Name of the person")
    description: str = Field(..., description="Description of the person")

    @classmethod
    def get_by_name(cls, name: str) -> Optional["Person"]:
        cypher = f"MATCH (n:{cls._label()} {{name: $name}}) RETURN id(n) AS node_id, n LIMIT 1"
        with session() as s:
            result = s.run(cypher, name=name)
            record = result.single()
            if not record:
                return None
            props = dict(record["n"]) if "n" in record else {}
            props["node_id"] = record["node_id"]
            return cls(**props)


class Event(Neo4jModel):
    name: str = Field(..., description="Name of the event")
    description: str = Field(..., description="Description of the event")

    @classmethod
    def get_by_name(cls, name: str) -> Optional["Event"]:
        cypher = f"MATCH (n:{cls._label()} {{name: $name}}) RETURN id(n) AS node_id, n LIMIT 1"
        with session() as s:
            result = s.run(cypher, name=name)
            record = result.single()
            if not record:
                return None
            props = dict(record["n"]) if "n" in record else {}
            props["node_id"] = record["node_id"]
            return cls(**props)

class HistoricalLocation(Neo4jModel):
    name: str = Field(..., description="Name of the historical location")
    description: str | None = Field(None, description="Description of the historical location")
    geojson: dict = Field(None, description="GeoJSON data representing the location's geometry")

    @classmethod
    def get_by_name(cls, name: str) -> Optional["HistoricalLocation"]:
        cypher = f"MATCH (n:{cls._label()} {{name: $name}}) RETURN id(n) AS node_id, n LIMIT 1"
        with session() as s:
            result = s.run(cypher, name=name)
            record = result.single()
            if not record:
                return None
            props = dict(record["n"]) if "n" in record else {}
            props["node_id"] = record["node_id"]
            return cls(**props)