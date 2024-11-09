import cfbd
import dotenv
import os


def create_client():
    configuration = cfbd.Configuration()
    dotenv.load_dotenv()
    configuration.api_key['Authorization'] = os.getenv('CFBD_API_TOKEN')
    configuration.api_key_prefix['Authorization'] = 'Bearer'

    return cfbd.ApiClient(configuration)
