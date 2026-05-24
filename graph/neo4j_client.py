# graph/neo4j_client.py
"""
Neo4j driver singleton.
Import get_driver() wherever you need a session.
"""
from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
    return _driver


def close_driver():
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


def run_query(cypher: str, params: dict = None) -> list:
    """
    Execute a Cypher query and return all records as a list of dicts.
    Use for READ queries.
    """
    driver = get_driver()
    with driver.session() as session:
        result = session.run(cypher, params or {})
        return [record.data() for record in result]


def run_write(cypher: str, params: dict = None) -> list:
    """
    Execute a Cypher write query inside an explicit write transaction.
    Use for CREATE / MERGE / SET queries.
    """
    driver = get_driver()
    with driver.session() as session:
        result = session.execute_write(
            lambda tx: list(tx.run(cypher, params or {}))
        )
        return result