import yaml
from yaml.loader import SafeLoader
import argparse
import time
from google.cloud import dataplex_v1, secretmanager
from google.protobuf import field_mask_pb2
from google.cloud import storage
from google.cloud.exceptions import NotFound
import pymsteams
from jira import JIRA
from typing import Optional
import logging
from datetime import datetime, timedelta



LOGGER: logging.Logger = logging.getLogger("utils")



BQ_PATH_TABLE= "projects/{0}/datasets/{1}/tables/{2}"
DATA_SCAN_PATH= "projects/{0}/locations/{1}/dataScans/{2}"
DATA_SCAN_ABSOLUTE_PATH="https://console.cloud.google.com/dataplex/group/quality/{0};location={1}?project={2}"
WEBHOOK_MS_TEAMS="path_to_webhook"
CREATION_LIMIT_TIME = 600
JOB_LIMIT_TIME = 7200
CHANNEL_NOTIFICATIONS = ['channel_notifications']

#Jita settings
JIRA_URL = 'path_to_jira'
PROJECT_KEY = 'path_to_project'

EPIC_KEY = 'path_to_epic'
EPIC_TYPE = 'Epica'
CARD_TYPE = 'Historia'
CARD_TYPE_QUERY = 'Story'
EPIC_LINK = 'customfield'

EPIC_SUMMARY = "Fix data quality alerts"
EPIC_DESCRIPTION = "Epica para enlazar cards de procesos que fallaron en el componente dataQuality"
CARD_SUMMARY = "Corregir el proceso: "

engineer_to_assign = 'email_to_assign'
account_id = None


#Método que trae el valor de un secreto tomando como parámetro el proyecto, el nombre del secreto y la versión(Alias)
def retrieve_secret(project_id , secret_name, secret_version):
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_name}/versions/{secret_version}"
    response = client.access_secret_version(name=name)
    
    return response.payload.data.decode("UTF-8")

#Métodos que leen la lista de secretos desde un archivo de configuración
def read_secrets(project_id, secrets):
    def retrieve_secret_value(secret):
        secret_name = secret["secret_name"]
        secret_version = secret["secret_version"]
        secret_value = retrieve_secret(project_id, secret_name, secret_version)
        return {"secret_value": secret_value, **secret}

    return [retrieve_secret_value(secret) for secret in secrets]


def get_secret_value(secrets, secret_name):
    return next((item["secret_value"] for item in secrets if item.get("secret_name") in secret_name), None)

def read_from_gcs(stg_client: storage.Client, bucket_name: str, blob: str) -> bytes:
    """
    Reads and return a blob from a GCS bucket.

    Arguments:
        stg_client: Storage client of BQ
        bucket_name: The GCS bucket where the desired file resides.
        blob: The blob path to the file.
    """
    bucket = stg_client.bucket(bucket_name)
    blob = bucket.blob(blob)

    return blob.download_as_string()


def get_config_from_gcs(stg_client: storage.Client, bucket, blob):
    """
    Parse job's information from the config file.
    """
    raw_config = read_from_gcs(stg_client, bucket, blob)
    parsed_config = yaml.load(raw_config, Loader=SafeLoader)

    return parsed_config

def parse_args():
    """
    Parse arguments from the caller.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("configbucket", help="The GCS bucket that contains the config files.")
    parser.add_argument("configblob", help="The GCS blob path to the config file")
    parser.add_argument("projectid", help="Project Id of BQ")
     # Argumentos opcionales
    parser.add_argument("--labelapplication", help="Label for application name", required=False, default="component-data-quality")
    parser.add_argument("--labelcostcenter", help="Label for cost center", required=False, default="equipo-data")
    parser.add_argument("--labelenvironment", help="Label for environment", required=False, default="")

    return vars(parser.parse_args())

def generate_data_scan(config, stg_client):

    project_id = config['projectid']
    dataset_id = config['bq_dataset']
    table_id = config['table_id']
    data_scan_id = config['data_scan_id']
    description = config['data_scan_description']
    display_name = config['data_scan_display_name']
    labels = config['labels']
    region = config['region']
    configbucket = config['configbucket']
    configblob = config['configblob']
    data_quality_spec_file = config['data_quality_spec_file']
    tagged_members = config.get('tagged_members',None)
    schedule_cron = config.get("schedule_cron",None)
    secret_channel_notifications = None
    if "secrets" in config:
        config["secrets"] = read_secrets(project_id,config["secrets"])
        secret_channel_notifications = get_secret_value(config["secrets"],CHANNEL_NOTIFICATIONS)
    
    if not secret_channel_notifications:
        secret_channel_notifications = WEBHOOK_MS_TEAMS

    directory = '/'.join(configblob.split('/')[:-1])
    data_quality_spec = get_config_from_gcs(stg_client, configbucket, f"{directory}/schema/{data_quality_spec_file}")

    post_scan_actions = data_quality_spec.get("post_scan_actions", {})

    if post_scan_actions:
        LOGGER.warning("se detectó flag post_action")
    # Si sí hay 'bigquery_export' definido, asegurarse que el formato de tabla sea correcto
        bigquery_export = post_scan_actions["bigquery_export"]
        if "results_table" in bigquery_export:
            results_table = bigquery_export["results_table"].split(".")
            data_quality_spec["post_scan_actions"]["bigquery_export"]["results_table"] = BQ_PATH_TABLE.format(project_id, results_table[0], results_table[1])
        LOGGER.warning("tabla personalizada")
    else:
        LOGGER.warning("no se detectó flag post_action")
        data_quality_spec["post_scan_actions"] = {
        "bigquery_export": {
            "results_table": BQ_PATH_TABLE.format("project", "ODS_NAME", "tb_name")  
            }
        }
        LOGGER.warning("tabla actualizada")

    data_scan = dataplex_v1.DataScan(
        data_quality_spec=data_quality_spec,
        description=description,
        display_name=display_name,
        labels=labels
    )
    if schedule_cron is not None:
        data_scan.execution_spec.trigger.schedule.cron = schedule_cron
        
    data_scan.data.resource = BQ_PATH_TABLE.format(project_id,dataset_id,table_id)
    # Create a client
    client = dataplex_v1.DataScanServiceClient()
    
    original_data_scan = get_data_scan(client,
                                       project_id,
                                       region,
                                       data_scan_id)

    if original_data_scan is None:
        create_data_scan(client, project_id,region,data_scan,data_scan_id)
    else:
        update_data_scan(client, original_data_scan, data_scan)

    if not wait_for_creation_completion(client,project_id,region,data_scan_id):
        LOGGER.warning("Data Scan will not be created.")
        return

    data_scan_path_job = run_data_scan(client,project_id,region,data_scan_id)

    if not wait_for_job_completion(client,data_scan_path_job):
        LOGGER.warning("Notifications will not be sent because the job was unsuccessful.")
        return

    send_notification(client,
                    project_id,
                    data_scan_path_job,
                    data_scan_id,
                    tagged_members,
                    secret_channel_notifications,
                    region)
    return


def run_data_scan(client,
                  project_id:str,
                  region:str,
                  data_scan_id:str):
    
    LOGGER.warning(f"Run Data scan: {data_scan_id}")

    # Initialize request argument(s)
    request = dataplex_v1.RunDataScanRequest(
        name=DATA_SCAN_PATH.format(project_id,region,data_scan_id),
    )

    # Make the request
    response = client.run_data_scan(request=request)

    # Handle the response
    LOGGER.warning(f"Executed successfully: {response.job.name} State: {response.job.state}")

    return response.job.name

def generate_update_mask(original_data_scan:dataplex_v1.DataScan,
                          modified_data_scan:dataplex_v1.DataScan):
    paths = []

    # Comparar campos individuales
    if original_data_scan.display_name != modified_data_scan.display_name:
        paths.append("display_name")
    if original_data_scan.description != modified_data_scan.description:
        paths.append("description")
    if original_data_scan.labels != modified_data_scan.labels:
        paths.append("labels")
    if original_data_scan.data_quality_spec.rules != modified_data_scan.data_quality_spec.rules:
        paths.append("data_quality_spec.rules")
    if original_data_scan.data_quality_spec.sampling_percent != modified_data_scan.data_quality_spec.sampling_percent:
        paths.append("data_quality_spec.sampling_percent")
    if original_data_scan.data_quality_spec.row_filter != modified_data_scan.data_quality_spec.row_filter:
        paths.append("data_quality_spec.row_filter")
    if original_data_scan.data_quality_spec.post_scan_actions != modified_data_scan.data_quality_spec.post_scan_actions:
        paths.append("data_quality_spec.post_scan_actions")
    if original_data_scan.execution_spec != modified_data_scan.execution_spec:
        paths.append("execution_spec")
    # Añadir otras comparaciones de campos según tus necesidades

    return field_mask_pb2.FieldMask(paths=paths)

def create_data_scan(client,
                     project_id:str,
                     region:str,
                     data_scan:dataplex_v1.DataScan,
                     data_scan_id:str):
    
    LOGGER.warning(f"Create Data scan: {data_scan_id}")

    request = dataplex_v1.CreateDataScanRequest(
            parent=f"projects/{project_id}/locations/{region}",
            data_scan=data_scan,
            data_scan_id=data_scan_id,
        )    

    # Make the request
    operation = client.create_data_scan(request=request,
                                        # publish=True
                                        # metadata=[("publish","true")]
                                        )

    LOGGER.warning("Waiting for operation to complete...")

    response = operation.result()

    # Handle the response
    LOGGER.warning(f"Created successfully: {response.name}")

    return
    
def update_data_scan(client,
                     original_data_scan:dataplex_v1.DataScan,
                     modified_data_scan:dataplex_v1.DataScan):
    
    LOGGER.warning(f"Update Data scan: {original_data_scan.name}")

    modified_data_scan.name = original_data_scan.name

    update_mask = generate_update_mask(original_data_scan, modified_data_scan)
    if(len(update_mask.paths) > 0):
        LOGGER.warning(f"Updating fields... {update_mask}")
        request = {
            "data_scan":modified_data_scan,
            "update_mask":update_mask
        }
        # Make the request
        operation = client.update_data_scan(
            #  name=f"projects/project/locations/location/dataScans/name_data_scan",
            request=request,
            # publish=True
            # metadata=[("publish","true")]
            )

        LOGGER.warning("Waiting for operation to complete...")

        response = operation.result()

        # Handle the response
        LOGGER.warning(f"Updated successfully: {response.name}")
    else:
        LOGGER.warning(f"No updates for: {original_data_scan.name}")
    
    return

def get_data_scan(client, 
                  project_id:str,
                  region:str,
                  data_scan_id:str):
    LOGGER.warning(f"Get Data scan: {data_scan_id}")
    
    # Initialize request argument(s)
    request = dataplex_v1.GetDataScanRequest(
        name=DATA_SCAN_PATH.format(project_id,region,data_scan_id),
        view="FULL" # sirve para ver toda la configuracion y resultado del proceso de calidad
    )

    try:
        response = client.get_data_scan(request=request)
        LOGGER.warning(f"Response uid: {response.uid}")
        # print(response)
        # return response.display_name
        return dataplex_v1.DataScan(
            name=response.name,
            display_name=response.display_name,
            description=response.description,
            data_quality_spec=response.data_quality_spec
        )
    except NotFound:
        LOGGER.warning("Data Scan {} is not found.".format(data_scan_id))
        return None

def get_data_result_scan(client,
                         project_id:str,
                         region:str,
                         data_scan_id:str):
    LOGGER.warning(f"Get Data Result Scan: {data_scan_id}")

    # Initialize request argument(s)
    request = dataplex_v1.GetDataScanRequest(
        name=DATA_SCAN_PATH.format(project_id,region,data_scan_id),
        view="FULL" # sirve para ver toda la configuracion y resultado del proceso de calidad
    )

    try:
        response = client.get_data_scan(request=request)
        LOGGER.warning(f"Response uid: {response.uid}")
        LOGGER.warning({
            response.uid,
            response.data_quality_result.row_count,
            response.data_quality_result.score,
            response.data_quality_result.passed,
            response.state
        })
        # return response.display_name
        return (response.uid,
                response.data_quality_result.row_count,
                response.data_quality_result.score,
                response.data_quality_result.passed,
                response.state)
    except NotFound:
        LOGGER.warning("Job Data Scan {} is not found.".format(data_scan_id))
        return None
    

    
def delete_data_scan(config):
    project_id = config['projectid']
    region = config['region']
    data_scan_id = config['data_scan_id']
    # Create a client
    client = dataplex_v1.DataScanServiceClient()

    # Initialize request argument(s)
    request = dataplex_v1.DeleteDataScanRequest(
        name=DATA_SCAN_PATH.format(project_id,region,data_scan_id),
    )

    # Make the request
    operation = client.delete_data_scan(request=request)

    LOGGER.warning("Waiting for operation to complete...")

    response = operation.result()

    # Handle the response
    LOGGER.warning(response)

def get_data_scan_job(client, data_scan_path_job:str):

    # Initialize request argument(s)
    request = dataplex_v1.GetDataScanJobRequest(
        name=data_scan_path_job,
        view="FULL" # sirve para ver toda la configuracion y resultado del proceso de calidad
    )

    # Make the request
    try:
        response = client.get_data_scan_job(request=request)
        LOGGER.warning(f"Response uid: {response.uid}")
        LOGGER.warning({response.uid,
                response.data_quality_result.row_count,
                response.data_quality_result.score,
                response.data_quality_result.passed,
                response.state})
        # return response.display_name
        return (response.uid,
                response.data_quality_result.row_count,
                response.data_quality_result.score,
                response.data_quality_result.passed,
                response.state)
    except NotFound:
        LOGGER.warning("Job Data Scan {} is not found.".format(data_scan_path_job))
        return None
    

def wait_for_creation_completion(client,
                                project_id,
                                region,
                                data_scan_id, 
                                poll_interval=10):
    result = False
    states = dataplex_v1.State
    current_time = 0
    while current_time<CREATION_LIMIT_TIME:
        uid,_,_,_,status = get_data_result_scan(client,
                                            project_id,
                                            region,
                                            data_scan_id)
        LOGGER.warning(f"State Data Quality Creation {uid}: {status}")
        
        if status == states.ACTIVE:
            LOGGER.warning(f"Data Scan {uid} completed")
            result = True
            break
        # elif job_status in [states.STATE_UNSPECIFIED]:
        #     LOGGER.warning(f"Job {job_id} did not complete successfully. Status: {job_status}")
        #     result = False
        #     break
        time.sleep(poll_interval)
        current_time+=poll_interval
    return result

def wait_for_job_completion(client,data_scan_path_job:str, poll_interval=10):
    states = dataplex_v1.DataScanJob.State
    result = False
    current_time = 0
    while current_time<JOB_LIMIT_TIME:
        job_id,_,_,_,job_status = get_data_scan_job(client,data_scan_path_job)
        LOGGER.warning(f"State Data Quality Job {job_id}: {job_status}")
        
        if job_status == states.SUCCEEDED:
            LOGGER.warning(f"Job {job_id} completed")
            result = True
            break
        elif job_status in [states.CANCELLED, states.FAILED]:
            LOGGER.warning(f"Job {job_id} did not complete successfully. Status: {job_status}")
            result = False
            break
        
        time.sleep(poll_interval)
        current_time+=poll_interval

    return result


def send_notification(client,
                    project_id:str,
                    data_scan_path_job:str,
                    data_scan_id:str,
                    tagged_members,
                    secret_channel_notifications,
                    region):

    LOGGER.warning(f"Send Notification: {data_scan_id}")

    job_id,row_count,score,passed,_ = get_data_scan_job(client,
                                                         data_scan_path_job
                                                         )

    if passed:
        LOGGER.warning(f"Job {job_id} Passed")
        return
    
    try:
        # Create Jira card for the failed data quality check
        card_summary = f"{CARD_SUMMARY} {data_scan_id}"
        card_key = find_or_create_jira_card(project_id, card_summary)
        
        message = pymsteams.connectorcard(secret_channel_notifications)

        # Añadir mencion a miembros
        message_text = f"Execution Quality Process {data_scan_id}"

        if tagged_members is not None and len(tagged_members) > 0:
            #Añadir menciones con el arroba
            tagged_text = " ".join([f"<at>{member}</at>" for member in tagged_members]) + " "
            message_text = f"{tagged_text} - {message_text}"

        # create the section
        message_section = pymsteams.cardsection()

        # Section Title
        message_section.title("Summary")

        # Facts are key value pairs displayed in a list.
        message_section.addFact("JOB ID:", job_id)
        message_section.addFact("ROW COUNT:", row_count)
        message_section.addFact("SCORE:", str(round(score, 2)))
        message_section.addFact("PASSED", passed)
        if card_key:
            message_section.addFact("JIRA CARD", card_key)
        
        
        # Add your section to the connector card object before sending
        message.addSection(message_section)
        
        message.text(message_text)
        message.color("#FF0000")
        message.addLinkButton("View Scan", DATA_SCAN_ABSOLUTE_PATH.format(data_scan_id,region,project_id))
        if card_key:
            jira_url = f"{JIRA_URL}/browse/{card_key}"
            message.addLinkButton("View Jira Card", jira_url)

        #message.send()
    except Exception as err:
        LOGGER.warning(f"Unexpected {err=}, {type(err)=}")
        raise Exception(repr(err))

    LOGGER.warning(f"Sending...")
    return


# client = dataplex_v1.DataScanServiceClient()
# job_id,row_count,score,passed,_ = get_data_result_scan(client,
#     "data-intelligence-350116",
#     "us-east1",
#     "ds-odsorder-tb-pse-transactions-0-968"
# )

# print(row_count)
# print(score)
# print(passed)

# send_notification(client,"project","projects/project/locations/us-east1/dataScans/ds-ods-tb-md-transbank/jobs/53657e77-7327-4839-bdf8-29ba58f70fd9","ds-ods-tb-md-transbank",["José Yon"],WEBHOOK_MS_TEAMS,"us-east1")
# job_id,row_count,score,passed,_ = get_data_scan_job(client,"projects/project/locations/us-east1/dataScans/ds-ods-tb-md-transbank/jobs/53657e77-7327-4839-bdf8-29ba58f70fd9")
# print(row_count)
# print(score)
# print(passed)
# print(result)

# update_data_scan(result)

# client = dataplex_v1.DataScanServiceClient()
# _ = get_data_scan(client,
#     project_id="project",
#     region="us-east1",
#     data_scan_id="ds-odsencuestas-tb-encuestasmtu")

class JiraConfig:
    """Configuration class for Jira connection and project settings."""
    
    def __init__(self, project_id: str, config: dict = None):
        # Jira Connection Settings
        self.JIRA_URL = JIRA_URL
        self.JIRA_USER = retrieve_secret(project_id, 'user_2', 'jira')
        self.JIRA_TOKEN = retrieve_secret(project_id, 'token', 'jira')
        
        # Project Settings
        self.PROJECT_KEY = PROJECT_KEY
        self.EPIC_TYPE = EPIC_TYPE
        self.EPIC_LINK = EPIC_LINK
        
        # Epic Settings
        self.EPIC_SUMMARY = EPIC_SUMMARY
        self.EPIC_DESCRIPTION = EPIC_DESCRIPTION
        self.EPIC_KEY = EPIC_KEY
        
        # Card Settings
        self.CARD_SUMMARY = CARD_SUMMARY
        self.CARD_TYPE = CARD_TYPE
        
        # User Settings
        self.engineer_to_assign = engineer_to_assign
        self.account_id = None

class JiraManager:
    """Class to manage Jira operations including user management, epic and Card creation."""
    
    def __init__(self, config: JiraConfig):
        self.config = config
        self.jira = JIRA(config.JIRA_URL, basic_auth=(config.JIRA_USER, config.JIRA_TOKEN))
    
    def get_user_account_id(self) -> Optional[str]:
        """Get the account ID for the assigned engineer."""
        try:
            users = self.jira.search_users(query=self.config.engineer_to_assign, maxResults=5)
            if users:
                LOGGER.warning(f"User found '{self.config.engineer_to_assign}':")
                for user in users:
                    LOGGER.warning(f"  Name: {user.displayName}, Account ID: {user.accountId}, Email: {user.emailAddress}")
                    self.config.account_id = user.accountId
                    LOGGER.warning(f"Determined user Account ID: **{self.config.account_id}**")
                    return self.config.account_id
            else:
                LOGGER.warning(f"No users found matching '{self.config.engineer_to_assign}'.")
                return None
        except Exception as e:
            LOGGER.error(f"Error searching for user '{self.config.engineer_to_assign}': {e}")
            return None

    def change_status(self, issue_key: str, transition_name: str) -> bool:
        """
        Change the status of a Jira issue.
        
        Args:
            issue_key: The key of the issue to transition
            transition_name: The name of the transition to apply
            
        Returns:
            bool: True if transition was successful, False otherwise
        """
        try:
            transitions = self.jira.transitions(issue_key)
            transition_id = next((t['id'] for t in transitions if t['name'] == transition_name), None)
            
            if transition_id:
                try:
                    self.jira.transition_issue(issue_key, transition_id)
                    LOGGER.warning(f"  -> Successfully transitioned issue {issue_key} to '{transition_name}'.")
                    return True
                except Exception as e:
                    LOGGER.error(f"  -> Error transitioning '{transition_name}' for issue {issue_key}: {e}")
                    return False
            else:
                LOGGER.warning(f"  -> Transition '{transition_name}' not found for issue {issue_key}.")
                return False
        except Exception as e:
            LOGGER.error(f"  -> Error getting transitions for issue {issue_key}: {e}")
            return False


    def create_card(self, epic_key: str, card_summary: str = None) -> Optional[str]:
        """Create a new card linked to an epic."""
        issue_dict = {
            'project': {'key': self.config.PROJECT_KEY},
            'summary': card_summary,
            'description': 'Cantidad de veces que falló el proceso: 1',
            'issuetype': {'name': self.config.CARD_TYPE},
            'assignee': {'accountId': self.config.account_id},
            'priority': {'name': 'Highest'},
            self.config.EPIC_LINK: epic_key
        }
        
        try:
            new_card = self.jira.create_issue(fields=issue_dict)
            LOGGER.warning(f"Successfully created card: {new_card.key}")
            return new_card.key
        except Exception as e:
            LOGGER.error(f"Error creating card: {e}")
            return None

def find_or_create_jira_card(project_id: str, card_summary: str = None) -> Optional[str]:
    """
    Create a Jira card for a data quality issue.
    
    Args:
        project_id: The GCP project ID
        card_summary: Optional custom summary for the card
        client: Optional DataScanServiceClient instance
        data_scan_path_job: Optional path to the data scan job
        
    Returns:
        Optional[str]: The created card key if successful, None otherwise
    """
    LOGGER.warning(f"Searching card '{card_summary}' in project '{PROJECT_KEY}'")
    find_card_query = (
         f'project = "{PROJECT_KEY}" AND '
         f'assignee = "{engineer_to_assign}" AND '
         f'type = {CARD_TYPE_QUERY} AND '
         f'summary ~ "{card_summary}" '
         'ORDER BY updated DESC'

    )
    
    try:
        # Initialize Jira configuration
        jira_config = JiraConfig(project_id)
        
        # Create Jira manager instance
        jira_manager = JiraManager(jira_config)

        # Get user account ID
        if not jira_manager.get_user_account_id():
            LOGGER.error("Failed to get user account ID. Exiting...")
            return None
        
        #Verify card existence
        cards = jira_manager.jira.search_issues(find_card_query, maxResults=1)
        if cards:
            target_card_key = cards[0].key
            LOGGER.warning(f"Found existing Card: {target_card_key} - {cards[0].fields.summary}")
            
            # Get current card status and description
            current_card = jira_manager.jira.issue(target_card_key)
            current_status = current_card.fields.status.name
            current_description = current_card.fields.description
            created_date = current_card.fields.created
            LOGGER.warning(f"Card details:\n  Card: {current_card}\n  Status: {current_status}\n Description: {current_description}\n Fecha de creación: {created_date}")

            
            # Extract current fail count
            fail_count = 0
            if current_description and "Cantidad de veces que falló el proceso:" in current_description:
                try:
                    fail_count = int(current_description.split(":")[-1].strip())
                except ValueError:
                    fail_count = 0

            # Update fail count and description
            fail_count += 1
            new_description = f"Cantidad de veces que falló el proceso: {fail_count}"
            current_card.update(description=new_description)
            LOGGER.warning(f"Updated card {target_card_key} with new fail count: {fail_count}")

            # Check if card was created 2 weeks ago and update summary with current date
            current_date = datetime.now()
            created_date = datetime.strptime(created_date.split('T')[0], '%Y-%m-%d') if created_date else None

            if created_date and (current_date - created_date).days >= 14:
                date_prefix = current_date.strftime('%Y-%m-%d')
                new_summary = f"[{date_prefix}] - {card_summary}"
                current_card.update(summary=new_summary)
                LOGGER.warning(f"Updated card {target_card_key} summary with date prefix: {new_summary}")

            status_transitions = {
                'LISTO PARA REVISION': ['Bloqueado', 'Por hacer'],
                'Bloqueado': ['Por hacer'],
                'Certificado': ['Bloqueado', 'Por hacer'],
                'Listo': ['Bloqueado', 'Por hacer'],
                'Refinando':['Por hacer']
            }
            # Update status
            for transition in status_transitions.get(current_status, []):
                jira_manager.change_status(target_card_key, transition)
                
            return target_card_key
        else:
            # Define epic
            epic_key = jira_config.EPIC_KEY

            # Create and transition card
            LOGGER.warning(f" Card '{card_summary}' not found.\nCreating a new card")
            card_key = jira_manager.create_card(epic_key, card_summary)
            if card_key:
                if jira_manager.change_status(card_key, 'En refinamiento'):
                    jira_manager.change_status(card_key, 'Por hacer')
                return card_key
                
            return None
    except Exception as e:
        LOGGER.error(f"Error creating Jira card: {e}")
        return None