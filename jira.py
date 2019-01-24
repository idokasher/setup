from jira import JIRA
import getpass

def send_os_command(command):
    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    stdout_data, stderr_data = p.communicate()
    retcode = p.returncode
    if (retcode == 0):
        raw_data = str(stdout_data, 'utf-8')
        raw_data_list = raw_data.split('\n')
        return (retcode, raw_data_list)
    else:
        if stderr_data:
            return (retcode, str(stderr_data, 'utf-8'))
        else:
            return (retcode, "None")

def send_mail(recipients, subject, body, user):
    recipients_str = ','.join(recipients)
    command = "cat <<'EOF' | /usr/sbin/sendmail -t -f %s" % user+ '\n'
    command += "to:%s" % recipients_str+ '\n'
    command += "subject:%s" % subject + '\n'
    command += body
    command += "\nEOF"
    os.system(command)


def create_parser():
    parser = argparse.ArgumentParser(description='Synchronizing respository with JIRA')
    parser.add_argument('--cl', help='CL', required=True)
    parser.add_argument('--issue', dest='issues', action='append', help='JIRA issue, may be repeated')
    parser.add_argument('--no-issue', help='no issues', action='store_true')
    return parser

def update_jira(release_note, cl, issues, no_issue):
    user = getpass.getuser()

    options = {'server': 'https://jira.company.com'}
    jira = JIRA(options, basic_auth=('myuser', 'mypass'))

    cl_field = ""
    release_note_field = ""
    for field in jira.fields():
        if field['name'] == 'Changeset':
            cl_field = field['id']
        elif field['name'] == 'Release Note':
            release_note_field = field['id']

        if cl_field != "" and release_note_field != "":
            break

    jira_issues = []
    jira_not_found = []

    for issue in issues:
        try:
            jira_issue = jira.issue(issue)
            jira_issues.append(jira_issue)
        except Exception as e:
            print(e)
            jira_not_found.append(issue)

    for jira_issue in jira_issues:

        orig_status = str(jira_issue.fields.status)
               
        # Skip JIRAs that are in one of the resolved states
        if (orig_status != "Fixed" and orig_status != "Accepted" and orig_status != "Closed" and orig_status != "Void" and orig_status != RESOLVED_STATUS):

            is_jira_ccr = (str(jira_issue.fields.issuetype) == ISSUE_TYPE_CCR)
            
            if is_jira_ccr:
                regression_test_name = jira_issue.raw['fields'][regression_test_field]

                if (orig_status == REPORTER_REVIEW_STATUS):
                    transition_name = FIX_ACCEPTED_TRANSITION
                else:
                    transition_name = FIXED_STATUS_TRANSITION

            else:
                # This is a JIRA story
                if (orig_status == REPORTER_REVIEW_STATUS):
                    transition_name = FIX_ACCEPTED_TRANSITION
                else:
                    transition_name = ACCEPTED_STATUS

            try:
                jira.transition_issue(jira_issue, transition_name)

                # In case this is a JIRA CCR in State Reporter Review, 2 state transitions are needed to get to Fixed, so adding the second one
                # A false error is expected if the "Previous State" was "Fixed" but this is not a main flow scenario
                if (is_jira_ccr and (orig_status == REPORTER_REVIEW_STATUS)):
                    transition_name = FIXED_STATUS_TRANSITION
                    jira.transition_issue(jira_issue, transition_name)
                    
            except Exception as error:
                if is_jira_ccr:
                    print("Cannot transit JIRA CCR %s to status 'Fixed' from '%s' using the '%s' transition" % (str(jira_issue), jira_issue.fields.status, transition_name) )
                else:
                    print("Cannot transit JIRA Story %s to status 'Accepted' from '%s' using the '%s' transition" % (str(jira_issue), jira_issue.fields.status, transition_name) )

                print ("Error: %s" % error)

            jira.add_comment(jira_issue, comment)
            release_note = release_note + "\n" + str(jira_issue.raw['fields'][release_note_field])
            jira_issue.update(fields={cl_field: cl, release_note_field: release_note})
            print("\n\nINFO: ")

        else:
            print("No transaction is required for issue: " + str(jira_issue) + " JIRA status is: " + str(jira_issue.fields.status))
    
    return ReturnValues.SUCCESS

def main(args): 
    parser = create_parser()
    args = parser.parse_args()
    return syncJIRAS(args.release_note, args.regression_test, args.cl, args.issues, args.no_issue)

