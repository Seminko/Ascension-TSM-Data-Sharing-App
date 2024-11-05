# %% LOCAL IMPORTS

from logger_config import logger
from generic_helper import prompt_yes_no

# %% MODULE IMPORTS

import subprocess
import xml.etree.ElementTree as ET
import os
from datetime import datetime
import re

# %% FUNCTIONS

def create_task_from_xml(task_name, exe_path, working_directory, xml_path):
    new_line_regex = r"(?:\n+|\s\s+)"
    if prompt_yes_no("Would you like to create a scheduled task so that the app runs on startup?"):
        create_task_xml(task_name, exe_path, working_directory, xml_path)
        try:
            # Create the task from the XML configuration file
            result = subprocess.run([
                'schtasks', '/create',
                '/tn', task_name,      # Task name
                '/xml', xml_path,      # Path to the XML file
                '/f'                   # Force creation (overwrite if exists)
            ], capture_output=True, text=True, check=True)
            # "stdout is not actually always english :("
            # if not "successfully been created" in result.stdout:
            #     raise Exception(re.sub(new_line_regex, " ", result.stdout).strip())
            logger.info(f"Scheduled task '{task_name}' created successfully")
        except subprocess.CalledProcessError as e:
            logger.critical(f"""Failed to create startup task. Error: '{re.sub(new_line_regex, " ", e.stderr).strip()}'""")
            logger.exception("Handled exception")
        except Exception as e:
            logger.critical(f"Failed to create startup task. Error: '{str(repr(e))}'")
            logger.exception("Handled exception")
        finally:
            try:
                os.remove(xml_path)
                logger.debug(f"Task definition XML '{xml_path}' removed successfully")
            except PermissionError as e:
                logger.debug(f"Removing task definition XML '{xml_path}' failed due to: '{str(repr(e))}'")
            except FileNotFoundError:
                logger.debug(f"Removing task definition XML '{xml_path}' failed due to: 'FileNotFoundError'")
                pass
    else:
        logger.debug("Trying to delete the task (in case it already exists and the setup was re-triggered)")
        delete_task(task_name)

def create_task_xml(task_name, exe_path, working_directory, xml_path):
    # Root element
    task = ET.Element('Task', attrib={
        'version': '1.3', 
        'xmlns': 'http://schemas.microsoft.com/windows/2004/02/mit/task'
    })

    # RegistrationInfo element
    registration_info = ET.SubElement(task, 'RegistrationInfo')
    date = ET.SubElement(registration_info, 'Date')
    date.text = str(datetime.now().isoformat(timespec='seconds'))
    author = ET.SubElement(registration_info, 'Author')
    author.text = 'Mortificator'
    description = ET.SubElement(registration_info, 'Description')
    description.text = 'Will run Ascension TSM Data Sharing App on user login'

    # Triggers element
    triggers = ET.SubElement(task, 'Triggers')
    logon_trigger = ET.SubElement(triggers, 'LogonTrigger')
    enabled = ET.SubElement(logon_trigger, 'Enabled')
    enabled.text = 'true'

    # Principals element (Run with highest privileges)
    principals = ET.SubElement(task, 'Principals')
    principal = ET.SubElement(principals, 'Principal', attrib={'id': 'Author'})
    logon_type = ET.SubElement(principal, 'LogonType')
    logon_type.text = 'InteractiveToken'
    run_level = ET.SubElement(principal, 'RunLevel')
    run_level.text = 'HighestAvailable'

    # Settings element
    settings = ET.SubElement(task, 'Settings')
    ET.SubElement(settings, 'MultipleInstancesPolicy').text = 'IgnoreNew'
    ET.SubElement(settings, 'DisallowStartIfOnBatteries').text = 'false'
    ET.SubElement(settings, 'StopIfGoingOnBatteries').text = 'false'
    ET.SubElement(settings, 'AllowHardTerminate').text = 'true'
    ET.SubElement(settings, 'StartWhenAvailable').text = 'true'
    ET.SubElement(settings, 'RunOnlyIfNetworkAvailable').text = 'true'
    idle_settings = ET.SubElement(settings, 'IdleSettings')
    ET.SubElement(idle_settings, 'StopOnIdleEnd').text = 'false'
    ET.SubElement(idle_settings, 'RestartOnIdle').text = 'false'
    ET.SubElement(settings, 'AllowStartOnDemand').text = 'true'
    ET.SubElement(settings, 'Enabled').text = 'true'
    ET.SubElement(settings, 'Hidden').text = 'false'
    ET.SubElement(settings, 'RunOnlyIfIdle').text = 'false'
    ET.SubElement(settings, 'WakeToRun').text = 'false'
    ET.SubElement(settings, 'ExecutionTimeLimit').text = 'PT0S'
    ET.SubElement(settings, 'Priority').text = '7'

    # Actions element (Executable command and working directory)
    actions = ET.SubElement(task, 'Actions', attrib={'Context': 'Author'})
    exec_action = ET.SubElement(actions, 'Exec')
    command = ET.SubElement(exec_action, 'Command')
    command.text = exe_path
    working_dir = ET.SubElement(exec_action, 'WorkingDirectory')
    working_dir.text = working_directory

    # Create the tree structure and write to the XML file
    tree = ET.ElementTree(task)

    # Write the tree to a file with UTF-16 encoding
    with open(xml_path, 'wb') as xml_file:
        tree.write(xml_file, encoding='utf-16', xml_declaration=True)

    logger.debug(f"Task definition XML file '{xml_path}' created successfully.")
    
def delete_task(task_name):
    new_line_regex = r"(?:\n+|\s\s+)"
    try:
        # Delete the task from Task Scheduler
        result = subprocess.run([
            'schtasks', '/delete',
            '/tn', task_name,
            '/f'  # Force deletion without confirmation
        ], capture_output=True, text=True, check=True)
        # "stdout is not actually always english :("
        # if not "successfully deleted" in result.stdout:
        #     raise Exception(result.stdout)
        logger.debug(f"Scheduled task '{task_name}' deleted successfully.")
    except subprocess.CalledProcessError as e:
        logger.debug(f"""Failed to delete startup task - probably because it doesn't exist / has never existed. Error: '{re.sub(new_line_regex, " ", e.stderr).strip()}'""")
    except Exception as e:
        logger.debug(f"Failed to delete startup task. Error: '{str(repr(e))}'")