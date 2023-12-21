import requests
import urllib.parse
from datetime import timezone, datetime
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']
calendar_id = 'primary'

def calendar_updated(creds, unique_channel_id):
    try:
        # Check if creds is valid
        if not creds or not creds.valid:
            exit()

        service = build('calendar', 'v3', credentials=creds)

        channel = {
                    'id': unique_channel_id,
                    'type': 'web_hook',
                    'address': 'https://3c88-223-178-208-185.ngrok-free.app/myapp/execute/'
                }

        watch_request = service.events().watch(calendarId=calendar_id, body=channel)

        response = watch_request.execute()

        # Extract events with tag "#" pattern
        now = datetime.now(timezone.utc).isoformat()
        events_result = service.events().list(
            calendarId='primary', q='#', timeMin=now).execute()
        events = events_result.get('items', [])

        for event in events:
            tag = None
            print('1-',tag)

            if 'summary' in event:
                event_title = event['summary'].strip().lower()
                if "#" in event_title:
                    tag_parts = event_title.split("#")
                    if len(tag_parts) > 1:
                        tag = tag_parts[1].split()[0]
                    else:
                        continue
                else:
                    continue

            if tag is None:
                continue

            print(tag)

            encoded_tag = urllib.parse.quote(tag)

            headers = {
                'Authorization': 'pk_72649265_2QJTM1SYMSIUCVWV4T6VG4K9B91WD17Z',
                # 'Authorization': 'pk_10657489_H8XHRQSY9H5DWGG2K8C55CD9QGC4XLTA',
                'Content-Type': 'application/json',
            }
            response = requests.get(
                f'https://api.clickup.com/api/v2/team/9016081736/task?tags[]={encoded_tag}&subtasks=true', headers=headers)
                # f'https://api.clickup.com/api/v2/team/20611636/task?tags[]={encoded_tag}&subtasks=true', headers=headers)


            tasks = response.json().get('tasks', [])

            # Print the tasks for debugging
            #print(json.dumps(tasks, indent=4))


            def get_orderindex(task):
                return int(task["priority"]["orderindex"]) if task.get("priority") else 99999
            tasks_sorted = sorted(tasks, key=get_orderindex)

            priority_colors = {
                "urgent": "red",
                "high": "#FFCC01",
                "normal": "lightblue",
                "low": "darkgray"
            }

            status_colors = {
                "to do": "red",
                "in progress": "#E16B16",
                "review/waiting on": "#FFCC01",
                "backburner": "darkgray"
            }

            def format_status(status):
                special_cases = {
                    "to do": "ToDo",
                    "review/waiting on": "Review/WaitingOn",
                    "in progress": "InProgress",
                    "backburner": "BackBurner"
                }
                return special_cases.get(status, status)

            # Create the dictionary before the loop
            tasks_dict = {task["id"]: task for task in tasks}

            for main_task in [t for t in tasks_sorted if not t.get('parent')]:
                main_task_id = main_task.get('id')

                if main_task.get('parent'):  # Task is a SubTask
                    print(
                        f"This is a subtask: {main_task['name']}. Task ID: {main_task.get('id')}")

                    parent_task_id = main_task.get('parent')
                    parent_task = tasks_dict.get(parent_task_id)

                    if parent_task:
                        # Add this sub-task to its parent task's sub-tasks list
                        parent_task_subtasks = parent_task.get('subtasks', [])
                        parent_task_subtasks.append(main_task)
                        parent_task['subtasks'] = parent_task_subtasks
                else:  # Task is a MainTask
                    print(f"This is a main task: {main_task['name']}")
                    if 'subtasks' not in main_task:
                        # Initialize empty subtasks list
                        main_task['subtasks'] = []

            task_data = response.json()

            description = "<br>"
            task_descriptions = []
            task_counter = 1  # Separate counter to manually manage task numbering

            for task in [t for t in tasks_sorted if not t.get('parent')]:
                print(f"Processing Main Task: {task['name']}")
                original_status = task['status']['status'].lower()
                status_value = format_status(original_status)
                status_color = status_colors.get(original_status, "")
                status_str = f"<br><strong>[S: <font color='{status_color}'>{status_value}</font>]</strong>"

                priority_str = ""
                if task.get("priority") and task["priority"]["priority"]:
                    priority_value = task["priority"]["priority"].lower()
                    priority_color = priority_colors.get(priority_value, "")
                    priority_str = f"<strong>[P: <font color='{priority_color}'>{priority_value.capitalize()}</font>]</strong>"

                due_date_str = ""
                if task.get("due_date"):
                    due_date_value = datetime.fromtimestamp(
                        int(task["due_date"]) / 1000, timezone.utc).strftime('%b-%d-%Y')
                    due_date_str = f"<strong>[DD: {due_date_value}]</strong>"

                time_str = ""
                if "time_estimate" in task and task["time_estimate"] is not None:
                    minutes = task["time_estimate"] / 60000
                    time_str = f"[{int(minutes)}m]"

                main_task_description = f"{task_counter}. {time_str}<a href='{task['url']}'>{task['name']}</a> {status_str} {priority_str} {due_date_str}<br>"
                # Add the main task description first
                task_descriptions.append(main_task_description)

                if "subtasks" in task and task["subtasks"]:

                    for subtask in task["subtasks"]:
                        print(f"Processing Sub-Task: {subtask['name']}")
                        subtask_status = subtask['status']['status'].lower()
                        subtask_status_value = format_status(subtask_status)
                        subtask_status_color = status_colors.get(
                            subtask_status, "")
                        subtask_status_str = f"<br><strong>  [S: <font color='{subtask_status_color}'>{subtask_status_value}</font>]</strong>"

                        subtask_desc = f"    ↳ <a href='{subtask['url']}'>{subtask['name']}</a> {subtask_status_str}<br>"
                        task_descriptions.append(subtask_desc)

                # Only increment the main task counter after processing main tasks and their subtasks
                task_counter += 1

            event['description'] = "\n".join(task_descriptions)
            updated_event = service.events().update(
                calendarId='primary', eventId=event['id'], body=event).execute()

            print("Events updated!")
            return 0
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return -1  # Return an error code to indicate failure

