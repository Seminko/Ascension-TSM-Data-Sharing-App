# from win10toast import ToastNotifier

# toast_notifier = ToastNotifier()

# def toast(title, msg, duration=5):
#     print(duration)
#     toast_notifier.show_toast(
#         title=title,
#         msg=msg,
#         duration=duration,
#         threaded=True
#     )
    
# toast("title", "kek", duration=15)



# from winrt.windows.ui.notifications import ToastNotificationManager, ToastNotification
# import winrt.windows.data.xml.dom as dom
# notifier = ToastNotificationManager.create_toast_notifier('TSM test')

# title = "kek"
# desp = "asdf"
# tString = """<toast duration='long'><audio src  = 'ms-winsoundevent:Notification.Reminder' loop = 'false' silent = 'false'/><visual><binding template='ToastText02'><text id="1">""" + title + """</text><text id="2">""" + desp + """</text></binding></visual></toast>"""

# xDoc = dom.XmlDocument()
# xDoc.load_xml(tString)
# notifier.show(ToastNotification(xDoc))


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