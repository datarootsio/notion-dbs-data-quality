import os

from Notion.NotionAPI import NotionAPI

if __name__ == "__main__":
    notion = NotionAPI(os.environ.get("NOTION_API_KEY"))
    print("Success!")
