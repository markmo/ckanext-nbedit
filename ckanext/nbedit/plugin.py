from ckan.common import config
from ckanext.nbedit import actions
from ckanext.nbedit.utils import merge_dict
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from urlparse import urljoin
import logging

log = logging.getLogger('ckanext-nbedit')


# Config settings

def jhub_base_url():
    return config.get('ckan.nbedit.jhub_base_url', '')


def jhub_api_url():
    return urljoin(jhub_base_url(), 'hub/api')


def jhub_public_proxy():
    return config.get('ckan.nbedit.jhub_public_proxy', '')


def jhub_token():
    return config.get('ckan.nbedit.jhub_token', '')


def jhub_token_expiry_sec():
    return config.get('ckan.nbedit.jhub_token_expiry_sec', '14400')


def redis_host():
    return config.get('ckan.redis.host', 'redis-master.default.svc.cluster.local')


def redis_password():
    return config.get('ckan.redis.password', '')


def instance_base_url():
    return config.get('ckan.api_url', 'http://192.168.99.100:32574/api')


def instance_host():
    return config.get('ckan.site_host', '192.168.99.100:32574')


class NbeditPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IResourceView)
    plugins.implements(plugins.IRoutes, inherit=True)
    plugins.implements(plugins.ITemplateHelpers)

    _is_server_running = False

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
            'start_server': actions.start_server,
            'stop_server': actions.stop_server,
            'jhub_user_exists_and_server_running': actions.jhub_user_exists_and_server_running,
            'create_jhub_user': actions.create_jhub_user,
            'add_user_to_group': actions.add_user_to_group,
            'create_user_token': actions.create_user_token
        }

    # ITemplateHelpers
    def get_helpers(self):
        return {
            'is_server_running': lambda: self._is_server_running
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
        return map

    # IResourceView

    def can_view(self, data_dict):
        supported_formats = ['ipynb']
        try:
            return data_dict['resource'].get('format', '').lower() in supported_formats
        except:
            return False

    def setup_template_variables(self, context, data_dict):
        log.debug('setup_template_variables')
        user_id = toolkit.c.userobj.id
        params = {
            'jhub_api_url': jhub_api_url(),
            'jhub_token': jhub_token(),
            'user_id': user_id
        }
        user_exists, server_is_running = \
            toolkit.get_action('jhub_user_exists_and_server_running')(context, params)

        if not user_exists:
            toolkit.get_action('create_jhub_user')(context, params)
            organization_list = \
                toolkit.get_action('organization_list_for_user')(context, { id: user_id })
            organization_id = organization_list[0]['id']
            toolkit.get_action('add_user_to_group')(
                context,
                merge_dict(params, { 'group_id': organization_id })
            )

        self._server_is_running = server_is_running

        token = toolkit.get_action('create_user_token')(
            context,
            merge_dict(params, { 'jhub_token_expiry_sec': jhub_token_expiry_sec() })
        )
        log.debug('token: ' + token)

        url = '{}/user/{}/tree/?token={}'.format(jhub_public_proxy(), user_id, token)
        base_url = '{}/user/{}/'.format(jhub_public_proxy(), user_id)
        log.debug('url: ' + url)
        log.debug('server_is_running: ' + str(server_is_running))
        return {
            'base_url': base_url,
            'jupyter_user_url': url,
            'server_is_running': server_is_running,
            'token': token
        }

    def view_template(self, context, data_dict):
        return 'nbedit/preview.html'

    def form_template(self, context, data_dict):
        return 'nbedit/form.html'
