import os
from contextlib import contextmanager
from typing import Optional
from neo4j import GraphDatabase
from neo4j import Driver
from dotenv import load_dotenv

load_dotenv()


class Neo4jDatabase:
    """Simple helper to manage a Neo4j driver instance.

    Environment variables used:
      - NEO4J_URI (default: bolt://localhost:7687)
      - NEO4J_USER
      - NEO4J_PASSWORD

    Use `get_driver()` to obtain the singleton driver instance and
    `session()` context manager to obtain a session for running queries.
    Remember to call `close_driver()` when shutting down the application.
    """

    _driver: Optional[Driver] = None

    @classmethod
    def init_driver(
        cls,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ) -> Driver:
        """Initialize the driver if not already initialized and return it."""
        if GraphDatabase is None:
            raise RuntimeError(
                "neo4j package is not installed. Add 'neo4j' to requirements.txt and install it"
            )

        if cls._driver is not None:
            return cls._driver

        uri = uri or os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        user = user or os.environ.get("NEO4J_USER")
        password = password or os.environ.get("NEO4J_PASSWORD")

        if user is None or password is None:
            raise RuntimeError(
                "NEO4J_USER and NEO4J_PASSWORD must be set in environment or passed to init_driver()"
            )

        cls._driver = GraphDatabase.driver(uri, auth=(user, password))
        return cls._driver

    @classmethod
    def get_driver(cls) -> Driver:
        """Return the singleton driver, initializing it from env if needed."""
        if cls._driver is None:
            return cls.init_driver()
        return cls._driver

    @classmethod
    def close_driver(cls) -> None:
        """Close and drop the singleton driver."""
        if cls._driver is not None:
            try:
                cls._driver.close()
            finally:
                cls._driver = None

    @classmethod
    def test_connection(cls) -> bool:
        """Test if the driver can connect to the database."""
        uri = os.environ.get("NEO4J_URI", "")
        print("URI: ", uri)
        user = os.environ.get("NEO4J_USER")
        password = os.environ.get("NEO4J_PASSWORD")
        auth = (user, password)
        print("Auth: ", auth)
        with GraphDatabase.driver(uri, auth=auth) as driver:
            driver.verify_connectivity()
            print("Connection successful")


@contextmanager
def session(read_only: bool = True):
    """Context manager yielding a Neo4j session.

    Example:
        from app.datamodels.database import session

        with session() as s:
            result = s.run("MATCH (n) RETURN count(n) AS c")
            value = result.single()["c"]
    """
    driver = Neo4jDatabase.get_driver()
    # Using simple session context; adapt to bolt protocol / access_mode if needed
    with driver.session() as s:
        yield s
