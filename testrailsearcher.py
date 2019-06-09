#
# TestRailSearcher
# python tool for full text searching in TestRail
#
# Learn more:
#
# https://github.com/cernyjan/testrailsearcher
#
# See license.md for details.
#

import getopt
from urllib.error import URLError

from testrail import *
import sys
import getpass
import ssl

ssl._create_default_https_context = ssl._create_unverified_context

tr_client = None
base_url = None
exit_message = "run with -h for help"
help_message = "testrailsearcher.py -s <server URL> -u <username>"
menu_message = ["p - select project", "s - select suite", "q - exit", "any key to next searching"]


def parse_input_parameters():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hs:u:', ['server=', 'username='])
    except getopt.GetoptError:
        print(help_message)
        sys.exit(2)
    global tr_client
    if len(opts) == 0:
        sys.exit(exit_message)
    if not any('-s' in o for o in opts):
        ask_for_server()
    for opt, arg in opts:
        if opt == '-h':
            print(help_message)
            sys.exit()
        elif opt in ('-s', '--server'):
            global base_url
            base_url = arg
            if not base_url.endswith('/'):
                base_url += '/'
            tr_client = APIClient(base_url)
        elif opt in ('-u', '--username'):
            tr_client.user = arg
        else:
            sys.exit(exit_message)


def validate_input(user_input, expected_type, max_value=None):
    if expected_type == 'integer':
        try:
            val = int(user_input)
            if max_value is None:
                return True
            if 0 <= val <= max_value:
                return True
            else:
                return False
        except ValueError:
            return False


def get_answer(question="Hit any key to continue press q to quit "):
    q = input(question)
    return q


def ask_for_server():
    global tr_client
    global base_url
    base_url = get_answer('server: ')
    if not base_url.endswith('/'):
        base_url += '/'
    tr_client = APIClient(base_url)


def ask_for_password():
    global tr_client
    tr_client.password = getpass.getpass('password: ')


def ask_for_credentials():
    global tr_client
    tr_client.user = get_answer('username: ')
    ask_for_password()


def try_login(first_attempt=False):
    if first_attempt and tr_client.user != '':
        ask_for_password()
    try:
        response = tr_client.send_get('get_user_by_email&email={}'.format(tr_client.user))
        print("logged as: {}".format(response['email']))
    except APIError as e:
        if "Invalid credentials" in e.args[0] or "Authentication failed" in e.args[0]:
            if get_answer("wrong credentials, hit any key to continue or press q to quit").lower() != 'q':
                ask_for_credentials()
                try_login()
    except (URLError, ValueError):
        if get_answer("wrong server url, hit any key to continue or press q to quit").lower() != 'q':
            ask_for_server()
            try_login()
    except Exception as ex:
        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        print(message)


def get_projects():
    try:
        response = tr_client.send_get('get_projects')
        return response
    except Exception as ex:
        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        print(message)


def get_suites(project_id):
    try:
        response = tr_client.send_get("get_suites/{}".format(project_id))
        return response
    except Exception as ex:
        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        print(message)


def get_cases(project_id, suite_id):
    try:
        response = tr_client.send_get("get_cases/{}&suite_id={}".format(project_id, suite_id))
        return response
    except Exception as ex:
        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        print(message)


def find_in_cases(cases, text):
    columns = ['id', 'title', 'custom_notes', 'custom_preconds', 'custom_custom_comments', 'custom_steps_separated']

    result = []
    for column in columns:
        temp_cases = [case for case in cases if case[column] is not None]
        if column == 'custom_steps_separated':
            temp_result = [case for case in temp_cases if
                           any(step for step in case[column] if text in step['content'] or text in step['expected'])]

        else:
            temp_result = [case for case in temp_cases if text in str(case[column])]
        result.extend(temp_result)

    cases = [i for n, i in enumerate(result) if i not in result[n + 1:]]
    print("found test cases: {}".format(len(cases)))
    return cases


def page_text(text_lined, num_lines=25, output_type='basic'):
    for index, line in enumerate(text_lined):
        if index % num_lines == 0 and index:
            if get_answer().lower() == 'q':
                break
        if output_type == 'basic':
            print("{} - {}".format(index, line['name']))
        if output_type == 'menu':
            print("{}".format(line))
        if output_type == 'result':
            global base_url
            print("| {} | {} |\n| {}\n|______ ".format("{}".format(line['id']).ljust(7), line['title'],
                                                       "{}{}{}".format(base_url, 'index.php?/cases/view/', line['id'])))


def main():
    print("{} - v{}".format("TestRail-Searcher", '1.0.0.0'))
    parse_input_parameters()
    try_login(True)
    change_project = True
    change_suite = True
    run = True
    project_id = -1
    suite_id = -1

    while run:
        if change_project:
            projects = get_projects()
            page_text(projects)
            project_number = ""
            while not validate_input(project_number, 'integer', len(projects) - 1):
                project_number = get_answer("project number: ")
            project_id = projects[int(project_number)]['id']
            change_project = False

        if change_suite:
            suites = get_suites(project_id)
            page_text(suites)
            suite_number = ""
            while not validate_input(suite_number, 'integer', len(suites) - 1):
                suite_number = get_answer("suite number: ")
            suite_id = suites[int(suite_number)]['id']
            change_suite = False

        text = get_answer("text: ")
        print('searching...')
        cases = get_cases(project_id, suite_id)
        found_cases = find_in_cases(cases, text)
        page_text(found_cases, output_type='result')

        page_text(menu_message, output_type='menu')
        choice = get_answer("menu: ")
        if choice.lower() == 'q':
            run = False
        if choice.lower() == 'p':
            change_project = True
        if choice.lower() == 's':
            change_suite = True


if __name__ == "__main__":
    main()
