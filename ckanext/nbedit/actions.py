import ckan.plugins.toolkit as toolkit
import requests
import logging

get_or_bust = toolkit.get_or_bust
log = logging.getLogger('ckanext-nbedit')


def start_server(context, data_dict):
    jhub_api_url = get_or_bust(data_dict, 'jhub_api_url')
    user_id = get_or_bust(data_dict, 'user_id')
    url = '{}/users/{}/server'.format(jhub_api_url, user_id)
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': 'token ' + get_or_bust(data_dict, 'user_token')
    }
    resp = requests.post(url, headers=headers, json={
        'kubespawner_override': {
            'environment': {
                'CKAN_API_TOKEN': get_or_bust(data_dict, 'ckan_api_token')
            }
        }
    })
    status_code = resp.status_code
    if status_code < 200 or status_code > 299:
        resp.raise_for_status()


def stop_server(context, data_dict):
    jhub_api_url = get_or_bust(data_dict, 'jhub_api_url')
    user_id = get_or_bust(data_dict, 'user_id')
    jhub_token = get_or_bust(data_dict, 'jhub_token')
    url = '{}/users/{}/server'.format(jhub_api_url, user_id)
    resp = requests.delete(url, headers=_jhub_headers(jhub_token))
    status_code = resp.status_code
    if status_code < 200 or status_code > 299:
        resp.raise_for_status()


@toolkit.side_effect_free
def jhub_user_exists_and_server_running(context, data_dict):
    jhub_api_url = get_or_bust(data_dict, 'jhub_api_url')
    user_id = get_or_bust(data_dict, 'user_id')
    jhub_token = get_or_bust(data_dict, 'jhub_token')
    url = '{}/users/{}'.format(jhub_api_url, user_id)
    resp = requests.get(url, headers=_jhub_headers(jhub_token))
    status_code = resp.status_code
    if status_code < 200 or status_code > 299:
        return (False, False)

    try:
        jhub_user = resp.json()
    except ValueError as err:
        log.error('JSON Decode Error: ' + str(err))
        log.error('response: ' + (resp.text if resp else 'None'))
        return (False, False)

    if not type(jhub_user) is dict:
        return (False, False)

    return (
        True if jhub_user['name'] else False,  # user exists
        True if jhub_user['server'] else False # server is running
    )


def create_jhub_user(context, data_dict):
    jhub_api_url = get_or_bust(data_dict, 'jhub_api_url')
    user_id = get_or_bust(data_dict, 'user_id')
    jhub_token = get_or_bust(data_dict, 'jhub_token')
    url = '{}/users/{}'.format(jhub_api_url, user_id)
    resp = requests.post(url, headers=_jhub_headers(jhub_token))
    status_code = resp.status_code
    if status_code < 200 or status_code > 299:
        resp.raise_for_status()


def add_user_to_group(context, data_dict):
    jhub_api_url = get_or_bust(data_dict, 'jhub_api_url')
    group_id = get_or_bust(data_dict, 'group_id')
    user_id = get_or_bust(data_dict, 'user_id')
    jhub_token = get_or_bust(data_dict, 'jhub_token')
    url = '{}/groups/{}/users'.format(jhub_api_url, group_id)
    resp = requests.post(url, headers=_jhub_headers(jhub_token), data={
        'users': [user_id]
    })
    status_code = resp.status_code
    if status_code < 200 or status_code > 299:
        resp.raise_for_status()


def create_user_token(context, data_dict):
    jhub_api_url = get_or_bust(data_dict, 'jhub_api_url')
    user_id = get_or_bust(data_dict, 'user_id')
    jhub_token = get_or_bust(data_dict, 'jhub_token')
    jhub_token_expiry_sec = get_or_bust(data_dict, 'jhub_token_expiry_sec')
    url = '{}/users/{}/tokens'.format(jhub_api_url, user_id)
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': 'token ' + jhub_token
    }
    payload = {
        'token_params': {
            'expires_in': jhub_token_expiry_sec,
            'note': 'Requested by ckanext-nbedit via API'
        }
    }
    resp = requests.post(url, headers=headers, json=payload)
    status_code = resp.status_code
    if status_code < 200 or status_code > 299:
        resp.raise_for_status()

    body = resp.json()
    return body['token'] if body else None


def _jhub_headers(jhub_token):
    return {
        'Accept': 'application/json',
        'Authorization': 'token ' + jhub_token
    }