from winrt.windows.ui.notifications import ToastNotificationManager, ToastNotification
import winrt.windows.data.xml.dom as dom

def create_update_notification(mandatory=False):
    # Create the toast notifier
    notifier = ToastNotificationManager.create_toast_notifier('Ascension TSM Data Sharing App')
    
    # Define the title, description, and URL
    if mandatory:
        title = "⚠️ MANDATORY UPDATE ⚠️"
        desc = "App WILL NOT run until you update!\nClick the button below, GitHub releases page will open in your default browser."
        url = "https://github.com/Seminko/Ascension-TSM-Data-Sharing-App/releases"
        scenario = " scenario='urgent'"
    else:
        title = "Update Available!"
        desc = "Click the button below, GitHub releases page will open in your default browser."
        url = "https://github.com/Seminko/Ascension-TSM-Data-Sharing-App/releases"
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
        <actions>
            <action content="Go to Github releases" activationType="protocol" arguments="{url}" />
        </actions>
    </toast>
    """
    
    # Load the XML content into the notification
    xDoc = dom.XmlDocument()
    xDoc.load_xml(tString)
    
    # Show the toast notification
    notifier.show(ToastNotification(xDoc))
    
def create_upload_reminder_notification(time_played):
    # Create the toast notifier
    notifier = ToastNotificationManager.create_toast_notifier('Ascension TSM Data Sharing App')
    
    # Define the title, description, and URL
    title = "Scan and Upload Reminder"
    desc = f"You have been playing for more than {int(time_played/60/60)}&#160;hours.&#10;Please consider doing an AH scan and /reload-ing to trigger DB upload.&#10;Thanks! ❤"

    tString = f"""
    <toast duration='long'>
        <audio src='ms-winsoundevent:Notification.Looping.Call10' loop='false' silent='true'/>
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
    
def create_generic_notification(title, desc):
    # Create the toast notifier
    notifier = ToastNotificationManager.create_toast_notifier('Ascension TSM Data Sharing App')
    
    tString = f"""
    <toast duration='long'>
        <audio src='ms-winsoundevent:Notification.Looping.Call10' loop='false' silent='true'/>
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