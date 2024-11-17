# %% LOCAL IMPORTS

from config import APP_NAME_WITHOUT_VERSION

# %% MODULE IMPORTS

from winrt.windows.ui.notifications import ToastNotificationManager, ToastNotification
import winrt.windows.data.xml.dom as dom

# %% FUNCTIONS

def create_generic_notification(title, desc, urgent=False):
    # Create the toast notifier
    notifier = ToastNotificationManager.create_toast_notifier(APP_NAME_WITHOUT_VERSION)
    scenario = ""
    ms_winsoundevent = "Notification.Default"
    if urgent:
        scenario = " scenario='urgent'"
        ms_winsoundevent = "Notification.Looping.Call10"
    
    tString = f"""
    <toast duration='long'{scenario}>
        <audio src='ms-winsoundevent:{ms_winsoundevent}' loop='false' silent='false'/>
        <visual>
            <binding template='ToastText02'>
                <text id='1'>{title}</text>
                <text id='2'>{desc}</text>
            </binding>
        </visual>
    </toast>
    
    """
    
    # Load the XML content into the notification
    xDoc = dom.XmlDocument()
    xDoc.load_xml(tString)
    
    # Show the toast notification
    notifier.show(ToastNotification(xDoc))

def create_update_notification(mandatory=False):
    # Create the toast notifier
    notifier = ToastNotificationManager.create_toast_notifier(APP_NAME_WITHOUT_VERSION)
    
    # Define the title, description, and URL
    if mandatory:
        title = "⚠️ MANDATORY UPDATE ⚠️"
        desc = "App WILL NOT run until you update!\nThe app is now paused and is waiting for your input."
        scenario = " scenario='urgent'"
    else:
        title = "Optional Update Available"
        desc = "Despite the update being optional, it would be better for everyone if you updated.\nThe app is now paused and is waiting for your input."
        scenario = ""
    
    # Toast XML with clickable description (action)
    tString = f"""
    <toast duration='long'{scenario}>
        <audio src='ms-winsoundevent:Notification.Looping.Call10' loop='false' silent='false'/>
        <visual>
            <binding template='ToastText02'>
                <text id='1'>{title}</text>
                <text id='2'>{desc}</text>
            </binding>
        </visual>
    </toast>
    """
    
    # Load the XML content into the notification
    xDoc = dom.XmlDocument()
    xDoc.load_xml(tString)
    
    # Show the toast notification
    notifier.show(ToastNotification(xDoc))