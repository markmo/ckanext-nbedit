from ckan.common import request
from ckanext.nbedit.utils import merge_dict
import ckan.plugins.toolkit as toolkit
import ckanext.nbedit.plugin as plugin
import io
import logging
import requests
import time

log = logging.getLogger('ckanext-nbedit')


class JServerController(toolkit.BaseController):

    def create(self):
        '''Start Jupyter Server.'''
        log.debug('Starting Jupyter Server...')
        try:
            # get query params
            id = request.GET.get('id')
            resource_id = request.GET.get('resource_id')
            view_id = request.GET.get('view_id')

            userobj = toolkit.c.userobj
            user_id = userobj.id
            ckan_api_token = userobj.apikey
            params = {
                'jhub_api_url': plugin.jhub_api_url(),
                'jhub_token': plugin.jhub_token(),
                'user_id': user_id
            }
            jhub_user_exists_and_server_running = \
                toolkit.get_action('jhub_user_exists_and_server_running')
            user_exists, server_is_running = \
                jhub_user_exists_and_server_running(None, params)

            if not user_exists:
                toolkit.get_action('create_jhub_user')(None, params)
                organization_list = \
                    toolkit.get_action('organization_list_for_user')(context, { id: user_id })
                organization_id = organization_list[0]['id']
                toolkit.get_action('add_user_to_group')(
                    None,
                    merge_dict(params, { 'group_id': organization_id })
                )

            token = toolkit.get_action('create_user_token')(
                None,
                merge_dict(params, { 'jhub_token_expiry_sec': plugin.jhub_token_expiry_sec() })
            )
            if not token:
                return toolkit.abort(
                    status_code=500,
                    detail='Invalid user token'
                )
            
            toolkit.get_action('start_server')(None, {
                'jhub_api_url': plugin.jhub_api_url(),
                'user_id': user_id,
                'user_token': token,
                'ckan_api_token': ckan_api_token,
                'oauth_client_id': '',
                'account_id': '',
                'instance_base_url': plugin.instance_base_url(),
                'instance_host': plugin.instance_host(),
                'authorization_server_url': '',
                'shared_secret': '',
                'space_key': '',
                'content_id': id,
                'redis_host': plugin.redis_host(),
                'redis_password': plugin.redis_password(),
                'notebook_server_image': plugin.notebook_server_image()
            })
            has_started = False
            retry_count = 0
            while not has_started and retry_count < 6:
                # TODO time for server to start
                time.sleep(10)
                retry_count += 1
                _, server_is_running = jhub_user_exists_and_server_running(None, params)
                log.debug('server_is_running: ' + str(server_is_running))
                if server_is_running:
                    has_started = True

            if not has_started:
                return toolkit.abort(
                    status_code=500,
                    detail='Could not start server'
                )

        except requests.exceptions.HTTPError as err:
            log.error('HTTP Error: ' + str(err))
            log.error('response: ' + err.response.text)
            return toolkit.abort(
                status_code=err.response.status_code,
                detail=str(err)
            )
        except requests.exceptions.TooManyRedirects:
            log.error('Bad URL')
            return toolkit.abort(status_code=500, detail=str(err))
        except requests.exceptions.ConnectionError:
            log.error('Connection Error: ' + str(err))
            return toolkit.abort(status_code=500, detail=str(err))
        except requests.exceptions.RequestException as err:
            log.error('Request Exception: ' + str(err))
            return toolkit.abort(status_code=500, detail=str(err))
        except ValueError as err:  # json.decode.JSONDecodeError in python 3
            log.error('JSON Decode Error: ' + str(err))
            return toolkit.abort(status_code=500, detail=str(err))
        except Exception as err:
            log.error(err)
            log.error('General Exception: ' + str(err))
            return toolkit.abort(status_code=500, detail=str(err))

        # must come outside the try block; the 302 is raising an exception
        toolkit.redirect_to(
            controller='package',
            action='resource_read',
            id=id,
            resource_id=resource_id,
            view_id=view_id
        )

    def delete(self):
        '''Stop Jupyter Server.'''
        log.debug('Stopping Jupyter Server...')
        try:
            user_id = toolkit.c.userobj.id
            params = {
                'jhub_api_url': plugin.jhub_api_url(),
                'jhub_token': plugin.jhub_token(),
                'user_id': user_id
            }
            jhub_user_exists_and_server_running = \
                toolkit.get_action('jhub_user_exists_and_server_running')

            toolkit.get_action('stop_server')(None, params)

            has_stopped = False
            retry_count = 0
            while not has_stopped and retry_count < 6:
                # TODO time for server to stop
                time.sleep(10)
                retry_count += 1
                _, server_is_running = jhub_user_exists_and_server_running(None, params)
                log.debug('server_is_running: ' + str(server_is_running))
                if not server_is_running:
                    has_stopped = True

            if not has_stopped:
                return toolkit.abort(
                    status_code=500,
                    detail='Could not stop server'
                )

            # get query params
            id = request.GET.get('id')
            resource_id = request.GET.get('resource_id')
            view_id = request.GET.get('view_id')

        except requests.exceptions.HTTPError as err:
            log.error('HTTP Error: ' + str(err))
            log.error('response: ' + err.response.text)
            return toolkit.abort(
                status_code=err.response.status_code,
                detail=str(err)
            )
        except requests.exceptions.TooManyRedirects:
            log.error('Bad URL')
            return toolkit.abort(status_code=500, detail=str(err))
        except requests.exceptions.ConnectionError:
            log.error('Connection Error: ' + str(err))
            return toolkit.abort(status_code=500, detail=str(err))
        except requests.exceptions.RequestException as err:
            log.error('Request Exception: ' + str(err))
            return toolkit.abort(status_code=500, detail=str(err))
        except ValueError as err:
            log.error('JSON Decode Error: ' + str(err))
            return toolkit.abort(status_code=500, detail=str(err))
        except Exception as err:
            log.error('General Exception: ' + str(err))
            return toolkit.abort(status_code=500, detail=str(err))

        # must come outside the try block; the 302 is raising an exception
        toolkit.redirect_to(
            controller='package',
            action='resource_read',
            id=id,
            resource_id=resource_id,
            view_id=view_id
        )


class NotebookController(toolkit.BaseController):

    def create(self, package):
        '''Create notebook'''
        log.debug('Creating notebook...')
        empty_notebook_file = io.StringIO(unicode(plugin.new_notebook_content()))
        try:
            package_info = toolkit.get_action('package_show')(None, { 'id': package })
            filelist = map(get_file, package_info['resources'])
            default_filename = plugin.new_notebook_filename()
            new_filename = default_filename

            # add an index number to the filename if it already exists
            i = 1
            while new_filename in filelist:
                new_filename = get_indexed_filename(default_filename, i)
                i += 1

            params = {
                'package_id': package,
                'name': new_filename,
                'format': 'ipynb',
                'mimetype': 'application/x-ipynb+json',
                'resource_type': 'file.upload',
                'upload': ('upload', empty_notebook_file)
            }
            resource = toolkit.get_action('resource_create')(None, params)
            # log.debug(resource)
            resource_id = resource['id']
            url = '{}/dataset/{}/resource/{}/download/{}'.format(
                plugin.site_url(), package_info['id'], resource_id, new_filename)

            # update resource with url
            toolkit.get_action('resource_update')(None, {
                'id': resource_id,
                'url': url
            })

        except Exception as err:
            log.error(err)
            log.error('General Exception: ' + str(err))
            return toolkit.abort(status_code=500, detail=str(err))

        toolkit.redirect_to(
            controller='package',
            action='resource_read',
            id=package,
            resource_id=resource_id,
            # view_id=view_id  # use default view
        )


def get_file(resource):
    url = resource['url']
    filename = url[url.rfind('/') + 1:]
    return filename


def get_indexed_filename(filename, index):
    name = filename[:filename.rfind('.')]
    return name + str(index) + '.ipynb'
