import getpass
from jira import JIRA
from tqdm import tqdm
import pandas as pd
from datetime import *
import time
from jira_references import *

# Jira Connection
def jira_connect(prompt_for_reconnect = False, existing_connection = None):
    needs_new_connection = False

    if existing_connection:
        j = existing_connection
        if prompt_for_reconnect: 
            print("Do you want to reconnect to JIRA? ('Y' to reconnect)")
            reconnect_input = input()
        
            if reconnect_input.strip().upper() in ("1","Y","YES"):
                needs_new_connection = True
    else:
        needs_new_connection = True
            
    if needs_new_connection:
        print("JIRA Username:")
        time.sleep(.25)
        un = input()
        print(" ")
        print("JIRA API Key (generated at https://id.atlassian.com/manage-profile/security/api-tokens):")
        time.sleep(.25)
        pw = getpass.getpass()
        
        j = JIRA("https://flightschedulepro.atlassian.net/", basic_auth=(un, pw))
        pw = ''
    
    return j

# def fetch_jira_issues_to_dataframe() # GET ALL TICKETS FOR A QUERY AND RETURN A DATAFRAME
def fetch_jira_issues_to_dataframe(jira_conn, jql_query):
    """
    Fetch issues from Jira based on a JQL query and return a DataFrame with specific fields.

    Parameters:
    jira_conn (JIRA): An authenticated JIRA connection object.
    jql_query (str): The JQL query to fetch issues.

    Returns:
    pd.DataFrame: A DataFrame containing issue key, status, resolution, created date, resolution date, issue type,
                  parent story, parent epic, and parent initiative.
    """
    issues = jira_conn.search_issues(jql_query, maxResults=False, expand='changelog', fields="key,summary,status,assignee,resolution,created,resolutiondate,issuetype,parent,customfield_10008,customfield_10009,customfield_10272,customfield_10022,fixVersions")
    
    #  customfield_10272 = Zendesk Ticket Count
    #  customfield_10008 = Epic Link
    #  customfield_10009 = Parent Link

    data = []
    for issue in tqdm(issues, desc="Processing issues"):
        
        issue_key = issue.key
        issue_summary = issue.fields.summary
        resolution = issue.fields.resolution.name if issue.fields.resolution else None
       
        # Issue Type values
        issue_type = issue.fields.issuetype.name
        issue_type_category = None
        
        if issue_type in PLANNING_ISSUE_TYPES:
            issue_type_category = 'PLANNING'
        elif issue_type in EPIC_ISSUE_TYPES:
            issue_type_category = 'EPIC'
        elif issue_type in STANDARD_ISSUE_TYPES:
            issue_type_category = 'STANDARD'
        elif issue_type in TESTING_ISSUE_TYPES:
            issue_type_category = 'TESTING'
        elif issue_type in SUB_TASK_ISSUE_TYPES:
            issue_type_category = 'SUBTASK'
        else:
            print(f"Unable to map issue type {issue_type} to issue_type_category")
        
        # Status values
        status = issue.fields.status.name
        status_category = None
        if status in DONE_STATUSES:
            status_category = 'Done'
        elif status in IN_VALIDATION_STATUSES:
            status_category = 'Validation'
        elif status in IN_DEV_STATUSES:
            status_category = 'Development'
        elif status in ENG_BACKLOG_STATUSES:
            status_category = 'Eng Backlog'
        elif status in PM_BACKLOG_STATUSES:
            status_category = 'PM Backlog'
        else:
            print(f"Unable to map status {status} to status_category")

        zendesk_ticket_count = getattr(issue.fields, 'customfield_10272', 0)
        zendesk_ticket_count = 0 if zendesk_ticket_count is None else zendesk_ticket_count

        story_points = getattr(issue.fields, 'customfield_10022', None)

        # Defect category
        defect_category = DEFECT_ISSUE_TYPES_TO_CATEGORY.get(issue_type, "Other")
        if zendesk_ticket_count > 0:
            defect_category = 'Customer Impacting Defect'
            
        # Print the fix versions (release versions) associated with the issue
        release_date = None
        release_version = None
        if hasattr(issue.fields, 'fixVersions'):
            for version in issue.fields.fixVersions:
                if hasattr(version, 'releaseDate'):
                    release_date_temp = pd.to_datetime(version.releaseDate).tz_localize(None)

                    if release_date is None or release_date_temp < release_date:
                        release_date = release_date_temp
                        release_version = version.name
                        
        # Dates 
        created_date_raw = issue.fields.created
        resolution_date_raw = issue.fields.resolutiondate if issue.fields.resolutiondate else None
        
        #print(f"{issue_key} - {created_date_raw} - {resolution_date_raw}")
        created_date = pd.to_datetime(created_date_raw).tz_localize(None)
        resolution_date = pd.to_datetime(resolution_date_raw).tz_localize(None) if resolution_date_raw else None
        
        # Pull historical status change dates.
        changelog = issue.changelog
        # Loop through the changelog to find when the status changed to "In Progress"
        pm_backlog_date = None
        eng_backlog_date = None
        dev_date = None
        validation_date = None
        done_date = None

        # get assignee
        assignee_email = None
        if issue.fields.assignee:
            assignee_email = issue.fields.assignee.emailAddress
    
        for history in changelog.histories:
            changed_date = history.created
            
            for item in history.items:
                changed_field = item.field
                new_value = item.toString

                if changed_field == "status":
                    if new_value in DONE_STATUSES:
                        # Take the max done date
                        if not done_date or changed_date > done_date:
                            done_date = changed_date
                    elif new_value in IN_VALIDATION_STATUSES:
                        # Take the min validation date
                        if not validation_date or changed_date < validation_date:
                            validation_date = changed_date
                    elif new_value in IN_DEV_STATUSES:
                        # take the min dev date
                        if not dev_date or changed_date <= dev_date:
                            dev_date = changed_date
                    elif new_value in ENG_BACKLOG_STATUSES:
                        # take the min backlog date
                        if not eng_backlog_date or changed_date < eng_backlog_date:
                            eng_backlog_date = changed_date

            
        # If the ticket is moved backwards, status dates can get weird.  Clean that up by removing dates from future stages
        if status in IN_VALIDATION_STATUSES:
            done_date = None
        elif status in IN_DEV_STATUSES:
            done_date = None
            validation_date = None
        elif status in ENG_BACKLOG_STATUSES:
            done_date = None
            validation_date = None
            dev_date = None
        elif status in PM_BACKLOG_STATUSES:
            done_date = None
            validation_date = None
            dev_date = None
            eng_backlog_date = None

        # Normalize dates
        done_date = pd.to_datetime(done_date).tz_localize(None) if done_date else None
        validation_date = pd.to_datetime(validation_date).tz_localize(None) if validation_date else None
        dev_date = pd.to_datetime(dev_date).tz_localize(None) if dev_date else None
        eng_backlog_date = pd.to_datetime(eng_backlog_date).tz_localize(None) if eng_backlog_date else None
        pm_backlog_date = created_date # default the PM backlog date to created

        # Cleanup tickets that don't have a resolution.
        if resolution is None and status == "Done":
            resolution = "Done"
            resolution_date = done_date
        elif resolution is None and status == "Won't Do":
            resolution = "Won't Do"
            resolution_date = done_date

            # skip this record and don't have it in the results set 
            continue

        # Bucket resolution & created dates to weeks for time series analysis
        if created_date is not None:
            created_week = created_date - pd.to_timedelta((created_date.weekday() + 1) % 7, unit='D')
            created_week = pd.to_datetime(created_week.date())
        else:
            created_week = None
        
        if resolution_date is not None:
            resolution_week = resolution_date - pd.to_timedelta((resolution_date.weekday() + 1) % 7, unit='D')
            resolution_week = pd.to_datetime(resolution_week.date())
        else:
            resolution_week = None
        
        # Map hierarchical values
        parent_story = None
        parent_epic = None
        parent_initiative = None
        parent_theme = None

        parent = issue.fields.parent.key if hasattr(issue.fields, 'parent') else None
        
        match issue_type_category:
            case "PLANNING":
                parent_theme = parent
            case "EPIC":
                parent_initiative = parent
            case "SUBTASK":
                # subtasks.  Parent = Story
                parent_story = parent
            case "STANDARD":
                # standard issue type
                parent_epic = parent
            case "TESTING":
                # no hierarchy
                pass
            case _:
                print(f"Unable to map heirarchy values for issue {issue_key}")
                
 
        data.append({
            'Issue Key': issue_key,
            'Summary': issue_summary,
            'Assignee': assignee_email,
            'Status': status,
            'Status Category': status_category,
            'Story Points': story_points,
            'Resolution': resolution,
            'Created Date': created_date,
            'Created Week': created_week,
            'PM Backlog Date': pm_backlog_date,
            'Eng Backlog Date': eng_backlog_date,
            'Development Date': dev_date,
            'Validation Date': validation_date,
            'Done Date': done_date,
            'Release Date': release_date,
            'Release Version': release_version,
            'Resolution Date': resolution_date,
            'Resolution Week': resolution_week,
            'Issue Type': issue_type,
            'Zendesk Ticket Count': zendesk_ticket_count,
            'Issue Type Category': issue_type_category,
            'Defect Category': defect_category,
            'Parent Story': parent_story,
            'Parent Story Name': None,
            'Parent Epic': parent_epic,
            'Parent Epic Name': None,
            'Parent Initiative': parent_initiative,
            'Parent Initiative Name': None,
            'Parent Theme': parent_theme
        })

    df = pd.DataFrame(data)

    # Second pass to populate the parent epic and parent initiative fields
    for i, row in df.iterrows():
        if row['Parent Initiative']:
            parent_initiative_row = df[df['Issue Key'] == row['Parent Initiative']]
            if not parent_initiative_row.empty:
                df.at[i, 'Parent Initiative Name'] = parent_initiative_row['Summary'].values[0]
                df.at[i, 'Parent Theme'] = parent_initiative_row['Parent Theme'].values[0]
                
    for i, row in df.iterrows():
        if row['Parent Epic']:
            parent_epic_row = df[df['Issue Key'] == row['Parent Epic']]
            if not parent_epic_row.empty:
                df.at[i, 'Parent Epic Name'] = parent_epic_row['Summary'].values[0]
                df.at[i, 'Parent Initiative'] = parent_epic_row['Parent Initiative'].values[0]
                df.at[i, 'Parent Initiative Name'] = parent_epic_row['Parent Initiative Name'].values[0]
                df.at[i, 'Parent Theme'] = parent_epic_row['Parent Theme'].values[0]

    for i, row in df.iterrows():
        if row['Parent Story']:
            parent_story_row = df[df['Issue Key'] == row['Parent Story']]
            if not parent_story_row.empty:
                df.at[i, 'Parent Story Name'] = parent_story_row['Summary'].values[0]
                df.at[i, 'Parent Epic'] = parent_story_row['Parent Epic'].values[0]
                df.at[i, 'Parent Epic Name'] = parent_story_row['Parent Epic Name'].values[0]
                df.at[i, 'Parent Initiative'] = parent_story_row['Parent Initiative'].values[0]
                df.at[i, 'Parent Initiative Name'] = parent_story_row['Parent Initiative Name'].values[0]
                df.at[i, 'Parent Theme'] = parent_story_row['Parent Theme'].values[0]

    return df