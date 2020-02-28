import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import logging
import os

from ckan.common import config
from ckanext.nbedit import actions
from ckanext.nbedit.utils import merge_dict
from urlparse import urljoin, urlparse

log = logging.getLogger('ckanext-nbedit')


# Config settings

def instance_base_url():
    url = config.get('ckan.site_url', '')
    return urljoin(url, 'api')


def instance_host():
    url = config.get('ckan.site_url', '')
    return urlparse(url).netloc


def jhub_base_url():
    return config.get('ckanext.nbedit.jhub_url', '').strip('/')


def jhub_api_url():
    return urljoin(jhub_base_url(), 'hub/api')


def jhub_public_proxy():
    return config.get('ckanext.nbedit.jhub_public_proxy', '')


def jhub_token():
    return config.get('ckanext.nbedit.jhub_token', '')


def jhub_token_expiry_sec():
    return config.get('ckanext.nbedit.jhub_token_expiry_sec', '14400')


def jupyter_root():
    return config.get('ckanext.nbedit.jupyter_root', 'ckan_project')


def nbviewer_host():
    return config.get('ckanext.nbview.nbviewer_host', '').strip('/')


def nested_tree():
    return toolkit.asbool(config.get('ckanext.nbview.nested_tree', False))


def new_notebook_content():
    return config.get('ckanext.nbedit.new_notebook_content',
        '{"cells":[{"cell_type":"code","source":[],"outputs":[],"execution_count":null,"metadata":{"trusted":true}}],"metadata":{"kernelspec":{"display_name":"Python 3","language":"python","name":"python3"},"nteract":{"version":"europa@0.1.0"},"language_info":{"name":"python","version":"3.7.4","mimetype":"text/x-python","codemirror_mode":{"name":"ipython","version":3},"pygments_lexer":"ipython3","nbconvert_exporter":"python","file_extension":".py"}},"nbformat":4,"nbformat_minor":2}')


def new_notebook_filename():
    return config.get('ckanext.nbedit.new_notebook_filename', 'notebook.ipynb')


def notebook_server_image():
    return config.get('ckanext.nbedit.notebook_server_image', None)


def redis_host():
    return config.get('ckanext.nbedit.jupyter_redis_host', '')


def redis_password():
    return config.get('ckanext.nbedit.jupyter_redis_password', '')

def site_url():
    return config.get('ckan.site_url', '')


class NbeditPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IOrganizationController, inherit=True)
    plugins.implements(plugins.IResourceView)
    plugins.implements(plugins.IRoutes, inherit=True)
    plugins.implements(plugins.ITemplateHelpers)

    def info(self):
        return {
            'name': 'nbedit',
            'title': toolkit._('Notebook Edit'),
            'default_title': toolkit._('Edit'),
            'icon': 'book',
            'always_available': True,
            'iframed': False
        }

    # IConfigurer
    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'nbedit')

    # IActions
    def get_actions(self):
        return {
            'add_user_to_group': actions.add_user_to_group,
            'create_jhub_group': actions.create_jhub_group,
            'create_jhub_user': actions.create_jhub_user,
            'create_user_token': actions.create_user_token,
            'jhub_user_exists_and_server_running': actions.jhub_user_exists_and_server_running,
            'start_server': actions.start_server,
            'stop_server': actions.stop_server
        }

    # ITemplateHelpers
    def get_helpers(self):
        return {
            'user_logged_in': lambda: toolkit.c.userobj is not None
        }

    # IRoutes
    def before_map(self, map):
        map.connect(
            'start-server',
            '/start-server',
            controller='ckanext.nbedit.controller:JServerController',
            action='create'
        )
        map.connect(
            'stop-server',
            '/stop-server',
            controller='ckanext.nbedit.controller:JServerController',
            action='delete'
        )
        map.connect(
            'new-notebook',
            '/dataset/new-notebook/{package}',
            controller='ckanext.nbedit.controller:NotebookController',
            action='create'
        )
        return map

    # IOrganizationController

    def create(self, entity):
        """Create matching JupyterHub Group for CKAN Organization."""
        group_id = entity.id
        log.debug('Creating group ' + group_id)
        params = {
            'group_id': group_id,
            'jhub_api_url': jhub_api_url(),
            'jhub_token': jhub_token()
        }
        toolkit.get_action('create_jhub_group')(None, params)
        return entity


    # IResourceView

    def can_view(self, data_dict):
        supported_formats = ['ipynb']
        try:
            resource = toolkit.get_or_bust(data_dict, 'resource')
            name, ext = os.path.splitext(resource.get('name', ''))
            ext = ext[1:].lower() if ext else ''
            log.debug("ext: '{}'".format(ext))
            result = (ext in supported_formats)
            log.debug('can_view? ' + str(result))
            return result
        except Exception as e:
            log.debug('Error: ' + str(e))
            log.debug('can_view? False')
            return False

    def setup_template_variables(self, context, data_dict):
        from urlparse import urlparse
        log.debug('setup_template_variables')
        resource_url = data_dict['resource']['url']
        parts = urlparse(resource_url)
        resource_url = parts.netloc + parts.path
        userobj = toolkit.c.userobj
        user_logged_in = userobj is not None
        nb_base_url = None
        server_is_running = False
        token = None
        if user_logged_in:
            user_id = userobj.id
            params = {
                'jhub_api_url': jhub_api_url(),
                'jhub_token': jhub_token(),
                'user_id': user_id
            }
            user_exists, server_is_running = \
                toolkit.get_action('jhub_user_exists_and_server_running')(context, params)

            log.debug('server_is_running: ' + str(server_is_running))

            if not user_exists:
                toolkit.get_action('create_jhub_user')(context, params)
                organization_list = \
                    toolkit.get_action('organization_list_for_user')(context, { id: user_id })
                organization_id = organization_list[0]['id']
                toolkit.get_action('add_user_to_group')(
                    context,
                    merge_dict(params, { 'group_id': organization_id })
                )

            token = toolkit.get_action('create_user_token')(
                context,
                merge_dict(params, { 'jhub_token_expiry_sec': jhub_token_expiry_sec() })
            )
            log.debug('token: ' + token)

            # url = '{}/user/{}/tree/?token={}'.format(jhub_public_proxy(), user_id, token)
            nb_base_url = '{}/user/{}/notebooks/'.format(jhub_public_proxy(), user_id)
            if nested_tree():
                root = jupyter_root()
                if root:
                    nb_base_url += '{}/'.format(root)

                nb_base_url += '{}/'.format(data_dict['package']['name'])

            log.debug('nb_base_url: ' + nb_base_url)

        return {
            # 'jupyter_user_url': url,
            'nb_base_url': nb_base_url,
            'nbviewer_host': nbviewer_host(),
            'resource_url': resource_url,
            'server_is_running': server_is_running,
            'token': token,
            'user_logged_in': user_logged_in
        }

    def view_template(self, context, data_dict):
        return 'nbedit/preview.html'

    def form_template(self, context, data_dict):
        return 'nbedit/form.html'
