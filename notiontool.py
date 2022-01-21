import utils
import requests
import json
from collections import defaultdict


config = utils.loadConfig()

BASE_URL = "https://api.notion.com/v1/"
NOTION_TOKEN = config['notionToken']
NOTION_VERSION = '2021-08-16'


def pull_config():
    notion_api = NotionApi(NOTION_TOKEN)
    response = notion_api.query_database(config['notionDatabaseId'])
    results = json.loads(response.text)["results"]
    site_indexes = {}
    new_config_sites = []
    for result in results:
        new_config_site = defaultdict(str)
        new_config_site["name"] = result["properties"]["name"]["title"][0]["text"]["content"]
        new_config_site["uri"] = result["properties"]["uri"]["url"]
        if result["properties"]["contentType"]["select"]:
            new_config_site["contentType"] = result["properties"]["contentType"]["select"]["name"]
        if result["properties"]["parserType"]["select"]:
            new_config_site["parserType"] = result["properties"]["parserType"]["select"]["name"]
        else:
            new_config_site["parserType"] = ""
        if result["properties"]["path"]["rich_text"]:
            new_config_site["path"] = result["properties"]["path"]["rich_text"][0]["text"]["content"]
        else:
            new_config_site["path"] = ""
        new_config_site["subscribers"] = [result["properties"]["subscribers"]["people"][i]["person"]["email"] for i in range(len(result["properties"]["subscribers"]["people"]))]
        new_config_sites.append(new_config_site)

    config["sites"] = new_config_sites
    utils.rewriteConfig(json.dumps(config, indent=4))


class NotionApi(object):
    """
    Everthing deal with notion api will be here. 
    """
    def __init__(self, token):
        self.token = token

    def query_database(self, database_id):
        path = BASE_URL + 'databases/{}/query'.format(database_id)
        headers = {'Authorization':'Bearer ' + self.token, 'Notion-Version':NOTION_VERSION}
        response = requests.post(path, headers=headers)
        return response
        

def _main():
    notion_api = NotionApi(NOTION_TOKEN)
    pull_config()


if __name__ == '__main__':
    _main()
