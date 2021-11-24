from typing import Union


class NotionRichTextObject:
    """Simple wrapper class for Notion's rich text object

    Official documentation:
        https://developers.notion.com/reference/rich-text
    """

    def __init__(self, rich_text_object: dict):
        """Initializes Notion's rich text object attributes

        Args:
          rich_text_object (dict): dictionary with attributes.
            Comes from a NotionPageProperty's value attribute.
        """

        self.plain_text = rich_text_object["plain_text"]
        self.href = rich_text_object["href"]
        self.annotations = rich_text_object["annotations"]
        self.type = rich_text_object["type"]

    def get_plain_text(self) -> str:
        """Getter for the plain_text attribute

        Returns:
            str: plain_text attribute
        """

        return self.plain_text


class NotionPageProperty:
    """Wrapper for Notion Page's Property attribute

    Official documentation:
        https://developers.notion.com/reference/page#property-value-object

    The property attribute in a Notion Page is the one that has all the
    custom information in the page.
    """

    def __init__(self, page_property: dict):
        """Initializes a Notion page property class given its dictionary

        Args:
          page_property (dict): dictionary with attributes.
            Comes from a Notion Page's property attribute
        """

        self.id = page_property["id"]
        self.type = page_property["type"]
        self.value = page_property[self.type]

    def get_value(self) -> Union[str, list[str], None]:
        """Returns the page property's value either as a
        string or a list of strings.

        Returns:
            Union[str, list[str], None]: page's property
        """

        if self.type == "checkbox":
            return self._get_checkbox_value()

        if not self.value:
            return None
        if self.type not in ["number"]:
            if len(self.value) == 0:
                return None

        type_to_function = {
            "title": self._get_title_value,
            "rich_text": self._get_rich_text_value,
            "relation": self._get_relation_value,
            "multi_select": self._get_multi_select_value,
            "phone_number": self._get_string_value,
            "rollup": self._get_rollup_value,
            "url": self._get_string_value,
            "date": self._get_string_value,
            "select": self._get_select_value,
            "email": self._get_string_value,
            "files": self._get_files_value,
            "number": self._get_number_value,
        }

        return type_to_function[self.type]()

    def _get_files_value(self) -> str:
        """Returns the value of a property of type files
        as a str
        """

        return self.value[0]["name"]

    def _get_select_value(self) -> str:
        """Returns the value of a property of type select
        as a string
        """

        return self.value["name"]

    def _get_rollup_value(self) -> str:
        """Returns the value of a property of type rollup
        as a string
        """

        property_type = self.value["type"]
        return self.value[property_type]

    def _get_number_value(self) -> int:
        """Returns the value of a property of type number"""

        return self.value

    def _get_checkbox_value(self) -> bool:
        """Returns the value of a property of type checkbox"""

        return self.value

    def _get_string_value(self) -> str:
        """Returns the value of a property of type string"""

        return self.value

    def _get_multi_select_value(self) -> list[str]:
        """Returns the value of a property of type multi_select
        as a list of strings
        """

        result = []

        for selection in self.value:
            result.append(selection["name"])
        return result

    def _get_relation_value(self) -> list[str]:
        """Returns the value of a property of type relation
        as a list of strings
        """

        result = []

        for relation in self.value:
            result.append(relation["id"])

        return result

    def _get_rich_text_value(self) -> str:
        """Returns the value of a property of type rich_text
        as a string
        """

        rich_text_object = NotionRichTextObject(self.value[0])
        return rich_text_object.get_plain_text()

    def _get_title_value(self) -> str:
        """Returns the value of a property of type title
        as a string
        """

        # check if there are more than 1 in the array
        # although why would there be more than 1 in a title?
        rich_text_object = NotionRichTextObject(self.value[0])
        return rich_text_object.get_plain_text()


class NotionPage:
    """Wrapper for a Notion Page

    Official documentation:
        https://developers.notion.com/reference/page
    """

    def __init__(self, json: dict):
        """Initializes a Notion page class given its dictionary

        Example of a json parameter json.loads(response.content) from
        an HTTP response

        Args:
          json (dict): content from a response to the Notion Page API
        """

        self.object = json["object"]
        self.id = json["id"]
        self.created_time = json["created_time"]
        self.last_edited_time = json["last_edited_time"]
        self.cover = json["cover"]
        self.icon = json["icon"]
        self.parent = json["parent"]
        self.archived = json["archived"]
        self.properties = json["properties"]
        self.url = json["url"]

    def get_properties_keys(self) -> dict:
        """Gets the keys from the properties attribute

        Returns:
            dict: properties keys
        """

        return self.properties.keys()

    def get_properties(self) -> dict:
        """Gets the properties of the Notion Page

        Returns:
            dict: properties
        """

        return self.properties

    def get_property(self, key: str) -> NotionPageProperty:
        """Gets a specific property

        Arguments:
            key (str): property key as a string

        Returns:
            NotionPageProperty: notion page property
        """

        # see if the key is valid
        return NotionPageProperty(self.properties[key])

    def get_property_value(self, key: str) -> str:
        """Gets the value of a specific property

        Arguments:
            key (str): property key as a string

        Returns:
            str: property value as a string
        """

        page_property = self.get_property(key)
        return page_property.get_value()
