import re
from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Dict
from typing import Iterable
from typing import Tuple

from elasticsearch7 import AsyncElasticsearch
from elasticsearch7 import Elasticsearch
from fastapi import HTTPException
from loguru import logger

from app.connectors.utils import get_connector_info_from_db
from app.connectors.wazuh_indexer.schema.indices import IndexConfigModel
from app.connectors.wazuh_indexer.schema.indices import Indices
from app.db.db_session import get_db_session


async def verify_wazuh_indexer_credentials(
    attributes: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Verifies the connection to Wazuh Indexer service.

    Returns:
        dict: A dictionary containing 'connectionSuccessful' status and 'authToken' if the connection is successful.
    """
    logger.info(
        f"Verifying the wazuh-indexer connection to {attributes['connector_url']}",
    )
    try:
        es = Elasticsearch(
            [attributes["connector_url"]],
            http_auth=(
                attributes["connector_username"],
                attributes["connector_password"],
            ),
            verify_certs=False,
            timeout=15,
            max_retries=10,
            retry_on_timeout=False,
        )
        es.cluster.health()
        logger.debug("Wazuh Indexer connection successful")
        return {
            "connectionSuccessful": True,
            "message": "Wazuh Indexer connection successful",
        }
    except Exception as e:
        logger.error(
            f"Connection to {attributes['connector_url']} failed with error: {e}",
        )
        return {
            "connectionSuccessful": False,
            "message": f"Connection to {attributes['connector_url']} failed with error: {e}",
        }


async def verify_wazuh_indexer_connection(connector_name: str) -> str:
    """
    Returns the authentication token for the Wazuh Indexer service.

    Returns:
        str: Authentication token for the Wazuh Indexer service.
    """
    async with get_db_session() as session:  # This will correctly enter the context manager
        attributes = await get_connector_info_from_db(connector_name, session)
    logger.info(
        f"Verifying the wazuh-indexer connection to {attributes['connector_url']}",
    )
    if attributes is None:
        logger.error("No Wazuh Indexer connector found in the database")
        return None
    return await verify_wazuh_indexer_credentials(attributes)


async def create_wazuh_indexer_client(connector_name: str = "Wazuh-Indexer") -> Elasticsearch:
    """
    Returns an Elasticsearch client for the Wazuh Indexer service.

    Returns:
        Elasticsearch: Elasticsearch client for the Wazuh Indexer service.
    """
    # attributes = get_connector_info_from_db(connector_name)
    async with get_db_session() as session:  # This will correctly enter the context manager
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        raise HTTPException(
            status_code=500,
            detail=f"No {connector_name} connector found in the database",
        )
    if attributes["connector_url"] == "https://127.1.1.1:9200":
        raise HTTPException(
            status_code=500,
            detail=f"Please update the {connector_name} connector URL",
        )
    try:
        return Elasticsearch(
            [attributes["connector_url"]],
            http_auth=(
                attributes["connector_username"],
                attributes["connector_password"],
            ),
            verify_certs=False,
            timeout=15,
            max_retries=10,
            retry_on_timeout=False,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create Elasticsearch client: {e}",
        )


async def create_wazuh_indexer_client_async(connector_name: str = "Wazuh-Indexer") -> AsyncElasticsearch:
    """
    Returns an Elasticsearch client for the Wazuh Indexer service.

    Returns:
        Elasticsearch: Elasticsearch client for the Wazuh Indexer service.
    """
    # attributes = get_connector_info_from_db(connector_name)
    async with get_db_session() as session:  # This will correctly enter the context manager
        attributes = await get_connector_info_from_db(connector_name, session)
    if attributes is None:
        raise HTTPException(
            status_code=500,
            detail=f"No {connector_name} connector found in the database",
        )
    if attributes["connector_url"] == "https://127.1.1.1:9200":
        raise HTTPException(
            status_code=500,
            detail=f"Please update the {connector_name} connector URL",
        )
    try:
        return AsyncElasticsearch(
            [attributes["connector_url"]],
            http_auth=(
                attributes["connector_username"],
                attributes["connector_password"],
            ),
            verify_certs=False,
            timeout=15,
            max_retries=10,
            retry_on_timeout=False,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create Elasticsearch client: {e}",
        )


async def format_node_allocation(node_allocation):
    """
    Format the node allocation details into a list of dictionaries. Each dictionary contains disk used, disk available, total disk, disk
    usage percentage, and node name.

    Args:
        node_allocation: Node allocation details from Elasticsearch.

    Returns:
        list: A list of dictionaries containing formatted node allocation details.
    """
    return [
        {
            "disk_used": node["disk.used"],
            "disk_available": node["disk.avail"],
            "disk_total": node["disk.total"],
            "disk_percent": node["disk.percent"],
            "node": node["node"],
        }
        for node in node_allocation
    ]


async def format_indices_stats(indices_stats):
    """
    Format the indices stats details into a list of dictionaries. Each dictionary contains the index name, the number of documents in the index,
    the size of the index, and the number of shards in the index.

    Args:
        indices_stats: Indices stats details from Elasticsearch.

    Returns:
        list: A list of dictionaries containing formatted indices stats details.
    """
    return [
        {
            "index": index["index"],
            "docs_count": index["docs.count"],
            "store_size": index["store.size"],
            "replica_count": index["rep"],
            "health": index["health"],
        }
        for index in indices_stats
    ]


async def format_shards(shards):
    """
    Format the shards details into a list of dictionaries. Each dictionary contains the index name, the shard number, the shard state, the shard
    size, and the node name.

    Args:
        shards: Shards details from Elasticsearch.

    Returns:
        list: A list of dictionaries containing formatted shards details.
    """
    return [
        {
            "index": shard["index"],
            "shard": shard["shard"],
            "state": shard["state"],
            "size": shard["store"],
            "node": shard["node"],
        }
        for shard in shards
    ]


# async def collect_indices() -> Indices:
#     """
#     Collects the indices from Elasticsearch.

#     Returns:
#         dict: A dictionary containing the indices, shards, and indices stats.
#     """
#     logger.info("Collecting indices from Elasticsearch")
#     es = await create_wazuh_indexer_client("Wazuh-Indexer")
#     try:
#         indices_dict = es.indices.get_alias("*", expand_wildcards="open")
#         indices_list = list(indices_dict.keys())
#         # Check if the index is valid
#         index_config = IndexConfigModel()
#         indices_list = [index for index in indices_list if index_config.is_valid_index(index)]
#         return Indices(
#             indices_list=indices_list,
#             success=True,
#             message="Indices collected successfully",
#         )
#     except Exception as e:
#         logger.error(f"Failed to collect indices: {e}")
#         raise HTTPException(status_code=500, detail=f"Failed to collect indices: {e}")


async def collect_indices(all_indices: bool = False) -> Indices:
    """
    Collects the indices from Elasticsearch.

    Args:
        all_indices (bool, optional): If True, all indices are listed. If False, only valid indices are listed. Defaults to False.

    Returns:
        dict: A dictionary containing the indices, shards, and indices stats.
    """
    logger.info("Collecting indices from Elasticsearch")
    es = await create_wazuh_indexer_client("Wazuh-Indexer")
    try:
        indices_dict = es.indices.get_alias("*", expand_wildcards="open")
        indices_list = list(indices_dict.keys())
        # Check if the index is valid
        if not all_indices:
            index_config = IndexConfigModel()
            indices_list = [index for index in indices_list if index_config.is_valid_index(index)]
        return Indices(
            indices_list=indices_list,
            success=True,
            message="Indices collected successfully",
        )
    except Exception as e:
        logger.error(f"Failed to collect indices: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect indices: {e}")


class AlertsQueryBuilder:
    @staticmethod
    def _get_time_range_start(timerange: str) -> str:
        """
        Determines the start time of the time range based on the current time and the provided timerange.

        Args:
            timerange (str): The time range to collect alerts from. This is a string like "24h", "1w", etc.

        Returns:
            str: A string representing the start time of the time range in ISO format.
        """
        if timerange.endswith("h"):
            delta = timedelta(hours=int(timerange[:-1]))
        elif timerange.endswith("d"):
            delta = timedelta(days=int(timerange[:-1]))
        elif timerange.endswith("w"):
            delta = timedelta(weeks=int(timerange[:-1]))
        else:
            raise ValueError(
                "Invalid timerange format. Expected a string like '24h', '1d', '1w', etc.",
            )

        start = datetime.utcnow() - delta
        return start.isoformat() + "Z"  # Elasticsearch expects the time in ISO format with a Z at the end

    def __init__(self):
        self.query = {
            "query": {
                "bool": {
                    "must": [],
                },
            },
            "sort": [],
        }

    def add_time_range(self, timerange: str, timestamp_field: str):
        """
        Adds a time range filter to the query.

        Args:
            timerange (str): The time range to filter by.
            timestamp_field (str): The name of the timestamp field in the index.

        Returns:
            self: The updated instance of the class.
        """
        start = self._get_time_range_start(timerange)
        range_query = {
            "range": {
                timestamp_field: {
                    "gte": start,
                    "lte": "now",
                },
            },
        }
        if timestamp_field == "timestamp":
            range_query["range"][timestamp_field]["format"] = "strict_date_optional_time"
        self.query["query"]["bool"]["must"].append(range_query)
        return self

    def add_matches(self, matches: Iterable[Tuple[str, str]]):
        """
        Adds matches to the query.

        Args:
            matches (Iterable[Tuple[str, str]]): A collection of field-value pairs to match.

        Returns:
            self: The current instance of the class.
        """
        for field, value in matches:
            self.query["query"]["bool"]["must"].append({"match": {field: value}})
        return self

    def add_match_phrase(self, matches: Iterable[Tuple[str, str]]):
        """
        Adds match phrases to the query.

        Args:
            matches (Iterable[Tuple[str, str]]): A collection of field-value pairs to match.

        Returns:
            self: The instance of the class.

        """
        for field, value in matches:
            self.query["query"]["bool"]["must"].append({"match_phrase": {field: value}})
        return self

    def add_range(self, field: str, value: str):
        """
        Adds a range query to the Elasticsearch query.

        Args:
            field (str): The field to apply the range query on.
            value (str): The value to compare against in the range query.

        Returns:
            self: The current instance of the class.
        """
        self.query["query"]["bool"]["must"].append({"range": {field: {"gte": value}}})
        return self

    def add_sort(self, field: str, order: str = "desc"):
        """
        Add a sort field to the query.

        Args:
            field (str): The field to sort by.
            order (str, optional): The sort order. Defaults to "desc".

        Returns:
            self: The updated instance of the class.
        """
        self.query["sort"].append({field: {"order": order}})
        return self

    def build(self):
        """
        Builds and returns the query.

        Returns:
            str: The built query.
        """
        return self.query


class LogsQueryBuilder:
    @staticmethod
    def _get_time_range_start(timerange: str) -> str:
        """
        Determines the start time of the time range based on the current time and the provided timerange.

        Args:
            timerange (str): The time range to collect alerts from. This is a string like "24h", "1w", etc.

        Returns:
            str: A string representing the start time of the time range in ISO format.
        """
        if timerange.endswith("m"):
            delta = timedelta(minutes=int(timerange[:-1]))
        elif timerange.endswith("h"):
            delta = timedelta(hours=int(timerange[:-1]))
        elif timerange.endswith("d"):
            delta = timedelta(days=int(timerange[:-1]))
        elif timerange.endswith("w"):
            delta = timedelta(weeks=int(timerange[:-1]))
        else:
            raise ValueError(
                "Invalid timerange format. Expected a string like '24h', '1d', '1w', '1m', etc.",
            )

        start = datetime.utcnow() - delta
        return start.isoformat() + "Z"  # Elasticsearch expects the time in ISO format with a Z at the end

    def __init__(self):
        self.query = {
            "query": {
                "bool": {
                    "must": [],
                },
            },
            "sort": [],
        }

    def add_time_range(self, timerange: str, timestamp_field: str):
        """
        Adds a time range filter to the query.

        Args:
            timerange (str): The time range to filter by.
            timestamp_field (str): The name of the timestamp field in the query.

        Returns:
            self: The updated instance of the class.
        """
        start = self._get_time_range_start(timerange)
        self.query["query"]["bool"]["must"].append(
            {"range": {timestamp_field: {"gte": start, "lte": "now"}}},
        )
        return self

    def add_matches(self, matches: Iterable[Tuple[str, str]]):
        """
        Adds matches to the query.

        Args:
            matches (Iterable[Tuple[str, str]]): A collection of field-value pairs to match.

        Returns:
            self: The current instance of the class.
        """
        for field, value in matches:
            self.query["query"]["bool"]["must"].append({"match": {field: value}})
        return self

    def add_match_phrase(self, matches: Iterable[Tuple[str, str]]):
        """
        Adds match phrases to the query.

        Args:
            matches (Iterable[Tuple[str, str]]): A collection of field-value pairs to match.

        Returns:
            self: The current instance of the class.
        """
        for field, value in matches:
            self.query["query"]["bool"]["must"].append({"match_phrase": {field: value}})
        return self

    def add_range(self, field: str, value: str):
        """
        Adds a range query to the Elasticsearch query.

        Args:
            field (str): The field to apply the range query on.
            value (str): The value to compare against in the range query.

        Returns:
            self: The instance of the class with the range query added.
        """
        self.query["query"]["bool"]["must"].append({"range": {field: {"gte": value}}})
        return self

    def add_sort(self, field: str, order: str = "desc"):
        """
        Adds a sort field to the query.

        Args:
            field (str): The field to sort by.
            order (str, optional): The sort order. Defaults to "desc".

        Returns:
            self: The updated instance of the class.
        """
        self.query["sort"].append({field: {"order": order}})
        return self

    def build(self):
        return self.query


async def get_index_mappings_key_names(index_name: str):
    """
    Get the mappings of an index.

    Args:
        index_name (str): The Name of the index.

    Returns:
        list: The field names of the index.
    """
    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
    mappings = es_client.indices.get_mapping(index=index_name)
    # return only the field names
    return list(mappings[index_name]["mappings"]["properties"].keys())


async def return_graylog_events_index_names():
    """
    Return the index names of the Graylog events.

    Returns:
        list: The index names of the Graylog events.
    """
    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
    indices = es_client.indices.get_alias("gl-events*")
    return list(indices.keys())


# async def get_index_source(index_name: str):
#     """
#     Get the 10 latest results from the index and search for where the source contains a field name of `syslog_type` or `integration`
#     """
#     es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
#     query = {"size": 10, "query": {"bool": {"must": [{"exists": {"field": "syslog_type"}}]}}}
#     response = es_client.search(index=index_name, body=query)
#     for hit in response["hits"]["hits"]:  # Loop through each hit in the response
#         if "syslog_type" in hit["_source"]:  # Check if 'syslog_type' exists in the source of the hit
#             if hit["_source"]["syslog_type"] == "integration" and "integration" in hit["_source"]:
#                 return hit["_source"]["integration"]  # Return the value of 'integration' if 'syslog_type' equals 'integration'
#             return hit["_source"]["syslog_type"]  # Return the value of 'syslog_type' for other cases
#     raise HTTPException(status_code=404, detail=f"Source not found in index {index_name}")


async def get_index_source(index_name: str):
    """
    Get the 10 latest results from the index and search for where the source contains a field name of `syslog_type` or `integration`
    """
    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")

    # First search for 'syslog_type'
    query_syslog_type = {"size": 10, "query": {"bool": {"must": [{"exists": {"field": "syslog_type"}}]}}}
    response = es_client.search(index=index_name, body=query_syslog_type)
    for hit in response["hits"]["hits"]:  # Loop through each hit in the response
        if "syslog_type" in hit["_source"]:  # Check if 'syslog_type' exists in the source of the hit
            if hit["_source"]["syslog_type"] == "integration" and "integration" in hit["_source"]:
                return hit["_source"]["integration"]  # Return the value of 'integration' if 'syslog_type' equals 'integration'
            return hit["_source"]["syslog_type"]  # Return the value of 'syslog_type' for other cases

    # If no 'syslog_type' found, search for 'integration'
    query_integration = {"size": 10, "query": {"bool": {"must": [{"exists": {"field": "integration"}}]}}}
    response = es_client.search(index=index_name, body=query_integration)
    for hit in response["hits"]["hits"]:  # Loop through each hit in the response
        if "integration" in hit["_source"]:  # Check if 'integration' exists in the source of the hit
            return hit["_source"]["integration"]  # Return the value of 'integration'

    raise HTTPException(status_code=404, detail=f"Source not found in index {index_name}")


async def get_available_indices_via_source(source: str):
    """
    Get the available indices based on the source using regex matching.

    Args:
        source (str): The regex pattern for the source of the index.

    Returns:
        list: The available indices based on the source regex match.
    """
    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")
    try:
        indices = es_client.indices.get_alias("*")
        logger.info(f"Indices: {indices.keys()}")
        available_indices = []
        source_pattern = re.compile(source)  # Compile the regex pattern for the source
        exclude_patterns = [re.compile("wazuh-monitoring"), re.compile("wazuh-statistics")]
        for index in indices.keys():
            if source_pattern.search(index) and not any(exclude.search(index) for exclude in exclude_patterns):
                available_indices.append(index)
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        available_indices = []

    logger.info(f"Available indices: {available_indices}")
    return available_indices


async def resize_wazuh_index_fields():
    """
    Resize the Wazuh index fields to the correct size.
    """
    es_client = await create_wazuh_indexer_client("Wazuh-Indexer")

    settings = {"index.mapping.total_fields.limit": 2000}

    try:
        es_client.indices.put_settings(index="wazuh*", body=settings)
        logger.info("Successfully resized the Wazuh index fields")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return None
