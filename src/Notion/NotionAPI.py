import json
import logging
from typing import Union

import pandas as pd
import requests
from requests.models import Response

from Notion.NotionPage import NotionPage


class NotionAPI:
    """Handler for Notion's API focused on its dbs.

    Includes methods to make raw GET and POST HTTP requests,
    but also wrappers like query_db() and get_page() which makes it easier to
    get the information you may want (e.g. all rows of a database as a pandas df).
    """

    logger = logging.getLogger("notion")

    def __init__(self, notion_api_key: str):
        """Constructor for NotionAPI class.
        Checks that the key has access to the API.

        Args:
          notion_api_key (str): Notion api key used to call Notion's API
        """

        self._add_notion_api_key(notion_api_key)

    def get_db_primary_key(self, db: str) -> str:
        """Returns the name of the column that acts as the db's pk

        Args:
          db (str): Notion's db. It can either be the full https link, or the dbid (either formatted or not)

        Returns:
            str: name of the column
        """

        if db.startswith("https"):
            db = self._extract_dbid_from_http_url(db)

        db = self.get_db(db)
        db_content = json.loads(db.content)

        for property in db_content["properties"].items():
            contents = property[1]
            if contents["type"] == "title":
                return contents["name"]

        # TODO: raise error that there is no column of type title

    def get_db_title(self, db: str) -> str:

        if db.startswith("https"):
            db = self._extract_dbid_from_http_url(db)

        db = self.get_db(db)
        db_content = json.loads(db.content)
        db_title = db_content["title"][0]["plain_text"]

        return db_title

    def query_db(
        self, db: str, query: str = "", return_type: str = "dataframe"
    ) -> Union[pd.DataFrame, list[dict], list[NotionPage]]:
        """Queries a database and returns the results in various possible formats (see arg 'return_type' for this).

        Official documentation:
            https://developers.notion.com/reference/post-database-query

        Args:
          db (str): Notion's db. It can either be the full https link, or the dbid (either formatted or not)
          query (str): Query to be sent. Leave empty to get all the rows back.
          return_type (str): Format in which you want the results back.
            Valid values are ["dataframe", "json", "NotionPage"]

        Returns:
            Union[pd.DataFrame, list[dict], list[NotionPage]]: the result of the query in the format asked for.
        """

        # TODO: check that return type is valid, raise error if not

        if db.startswith("https"):
            db = self._extract_dbid_from_http_url(db)
        # TODO: need to add an if-else check that the dbid is valid or needs formatting

        self.logger.info(f"Attempting to query databse {db}")
        headers = self._build_headers()
        data = f"{query}"

        response = self.post_request(
            f"https://api.notion.com/v1/databases/{db}/query",
            headers=headers,
            data=data,
        )

        json_content = json.loads(response.content)
        json_results = json_content["results"]

        # keep querying while there are more rows (max is 100 per call)
        while json_content["has_more"]:
            next_cursor = json_content["next_cursor"]
            data = dict()
            data["start_cursor"] = next_cursor
            response = self.post_request(
                f"https://api.notion.com/v1/databases/{db}/query",
                headers=headers,
                json_arg=data,
            )
            json_content = json.loads(response.content)
            json_results += json_content["results"]

        # convert to list of NotionPage objects
        notion_pages = []
        for page in json_results:
            notion_pages.append(NotionPage(page))

        if return_type == "json":
            return json_results
        elif return_type == "dataframe":
            return self.pages_to_dataframe(notion_pages)
        elif return_type == "NotionPage":
            return notion_pages

    def get_page(self, page_id: str) -> Response:
        """Queries the Notion API for a specific page and returns it.

        Official documentation:
            https://developers.notion.com/reference/retrieve-a-page

        Args:
          page_id (str): Notion's page id. It can be formatted or not.

        Returns:
            Response: the response from the Notion API
        """

        base_request = self._get_base_url() + "pages"

        # TODO: check that page_id format is somewhat right
        # TODO: check if page_id is not formatted already
        page_id = self._format_page_id(page_id)

        # build and send get request
        request_url = f"{base_request}/{page_id}"
        headers = self._build_headers()
        response = self.get_request(request_url, headers)

        # check if response is 200
        if response.status_code != 200:
            raise ValueError("Did not get response 200")

        response = NotionPage(json.loads(response.content))

        return response

    def get_db(self, db_id: str) -> Response:
        """Queries the Notion API for a specific database and returns it.

        Official documentation:
            https://developers.notion.com/reference/retrieve-a-database

        Note:
            it does not return the rows, but rather the schema and other information.

        Args:
          db_id (str): Notion's db id. It can be formatted or not.

        Returns:
            Response: the response from the Notion API
        """

        base_request = self._get_base_url() + "databases"

        # check if page_id is not formatted already
        db_id = self._format_page_id(db_id)

        # build and send get request
        request_url = f"{base_request}/{db_id}"
        headers = self._build_headers()
        response = self.get_request(request_url, headers)

        return response

    def _add_notion_api_key(self, key: str):
        """Internal method used by __init__.
        Sets the instance variable for the api key.
        Checks minimally for string-matching correctness and checks that the key
        can call the API correctly with a dumb call.
        """

        self.NOTION_API_KEY = key

        # validate key
        if not key:
            raise SystemExit("Received None as NOTION_API_KEY")
        elif not key.startswith("secret"):
            raise SystemExit("Given NOTION_API_KEY does not start with 'secret'.")

        # validate connection
        self._check_connection()

    def _check_connection(self):
        """Internal method used by _add_notion_api_key.
        Checks validity of the key by making a dumb query to the API.
        """

        headers = self._build_headers()
        self.get_request("https://api.notion.com/v1/users", headers)

    def _build_headers(self) -> dict:
        """Builds basic headers as Notion's API expects them."""

        headers = {
            "Notion-Version": "2021-08-16",
            "Authorization": f"Bearer {self.NOTION_API_KEY}",
        }

        return headers

    def get_request(self, request_url: str, headers: dict) -> Response:
        """Sends a GET HTTP request to Notion's API.
        Returns the response, checking for errors.

        Args:
          request_url (str): Request url to be used for the HTTP request.
          headers (dict): Headers to be used for the HTTP request.
            See method self._build_headers for this

        Returns:
            Response: the response from the Notion API
        """

        try:
            response = requests.get(request_url, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            self.logger.error(
                f"Received http response: {response.status_code}. Reason: {response.reason}"
            )
            raise SystemExit(e)

        return response

    def post_request(
        self, request_url: str, headers: dict, data: str = None, json_arg: dict = None
    ) -> Response:
        """Sends a POST HTTP request to Notion's API.
        Returns the response, checking for errors.

        Args:
          request_url (str): Request url to be used for the HTTP request.
          headers (dict): Headers to be used for the HTTP request.
            See method self._build_headers for this
          data (str): string to be sent in the 'data' field of the request.
          json_arg (dict): data to be sent as json data in the request.
            Note: the requests library converts this dict to json internally.

        Returns:
            Response: the response from the Notion API
        """

        try:
            response = requests.post(
                request_url, headers=headers, data=data, json=json_arg
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            self.logger.error(
                f"Received http response: {response.status_code}. Reason: {response.reason}"
            )
            raise SystemExit(e)

        return response

    @staticmethod
    def pages_to_dataframe(notion_pages: list[NotionPage]) -> pd.DataFrame:
        """Receives a list of NotionPage objects and flattens them into a
        pandas dataframe.

        Args:
          notion_pages (list[NotionPage]): list of NotionPage objects.

        Returns:
            pd.DataFrame: pandas dataframe with the information flattened.
        """

        # TODO: check validity of notion_pages

        columns = notion_pages[0].get_properties_keys()
        df = pd.DataFrame(columns=columns)

        for x, page in enumerate(notion_pages):
            property_keys = page.get_properties_keys()
            for key in property_keys:
                value = page.get_property_value(key)
                df.at[x, key] = value

        return df

    @staticmethod
    def _format_page_id(raw_id: str) -> str:
        """Receives a raw_id and adds dashes in the format
        which Notion's API expects it in.
        """

        # TODO: check for page_id length

        # insert dashes for 8-4-4-4-12 structure
        result = raw_id[0:8] + "-"
        result += raw_id[8:12] + "-"
        result += raw_id[12:16] + "-"
        result += raw_id[16:20] + "-"
        result += raw_id[20:]

        return result

    @staticmethod
    def _get_base_url() -> str:
        """Returns Notion's API base url."""

        return "https://api.notion.com/v1/"

    @staticmethod
    def _extract_dbid_from_http_url(http_url: str) -> str:
        """Receives a full https url string and extracts the db id."""

        view_position_index = http_url.find("?v=")
        initial_pos = view_position_index - 32
        db_id = http_url[initial_pos:view_position_index]
        return db_id
