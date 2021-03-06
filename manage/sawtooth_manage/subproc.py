# Copyright 2016 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ------------------------------------------------------------------------------

import os
import signal
import subprocess
import time
import re
import sys
import traceback
import yaml

from sawtooth_manage.node import NodeController
from sawtooth_manage.exceptions import ManagementError


def _get_executable_script(script_name):
    '''
    Searches PATH environmental variable to find the information needed to
    execute a script.
    Args:
        script_name:  the name of the 'executable' script
    Returns:
        ret_val (list<str>): A list containing the python executable, and the
        full path to the script.  Includes sys.executable, because certain
        operating systems cannot execute scripts directly.
    '''
    ret_val = None
    if 'PATH' not in os.environ:
        raise ManagementError('no PATH environmental variable')
    search_path = os.environ['PATH']
    for directory in search_path.split(os.pathsep):
        if os.path.exists(os.path.join(directory, script_name)):
            ret_val = os.path.join(directory, script_name)
            break
    if ret_val is not None:
        ret_val = [sys.executable, ret_val]
    else:
        raise ManagementError("could not locate %s" % (script_name))
    return ret_val


class SubprocessNodeController(NodeController):
    def __init__(self, state_dir=None):
        if state_dir is None:
            state_dir = \
                os.path.join(os.path.expanduser("~"), '.sawtooth', 'cluster')

        if not os.path.exists(state_dir):
            os.makedirs(state_dir)
        self._state_dir = state_dir
        self._state_file_path = os.path.join(self._state_dir, 'state.yaml')

    def _load_state(self):
        return yaml.safe_load(open(self._state_file_path))

    def _save_state(self, state):
        with open(self._state_file_path, 'w') as state_file:
            yaml.dump(state, state_file, default_flow_style=False)

    def start(self, node_args):
        state = self._load_state()

        node_name = node_args.node_name
        node_num = int(node_name[len('validator-'):])

        base_component_port = 40000
        port = str(base_component_port + node_num)
        url = 'tcp://0.0.0.0:' + port

        base_gossip_port = 8800
        gossip_port_num = str(base_gossip_port + node_num)
        gossip_port = 'tcp://0.0.0.0:' + gossip_port_num

        state['Nodes'][node_name]['pid'] = []

        commands = ['validator'] + state['Processors']
        if node_args.genesis:
            commands = ['sawtooth'] + commands + ['rest_api']
            # clean data dir of existing genesis node artifacts
            data_dir = os.path.join(os.path.expanduser("~"),
                                    'sawtooth', 'data')
            regex = re.compile('.*')
            self._rm_wildcard(data_dir, regex)

        for cmd in commands:
            # _get_executable_script returns (path, executable)
            _, executable = _get_executable_script(cmd)

            # validator takes ports as separate args, but this might change
            if cmd == 'validator':
                component = '--component-endpoint', url
                network = '--network-endpoint', gossip_port
                public_uri = '--public-uri', 'tcp://localhost:{}'.\
                    format(gossip_port_num)
                peer_list = ['tcp://localhost:' + str(base_gossip_port + i)
                             for i in range(node_num)]
                peers = ['--peers']
                peer_list_comma_sep = [",".join(peer_list)]
                peers.extend(peer_list_comma_sep)
                if peers:
                    peers_flag = tuple(peers)
                flags = component + network + public_uri
                if len(peer_list) > 0:
                    flags += peers_flag

            elif cmd == 'sawtooth':
                flags = 'admin', 'genesis'
            elif cmd == 'rest_api':
                flags = '--stream-url', url
            else:
                flags = (url,)
            handle = subprocess.Popen((executable,) + flags)

            pid = handle.pid
            state['Nodes'][node_name]['pid'] += [pid]

        self._save_state(state)

        if node_args.genesis:
            time.sleep(5)

    def _send_signal_to_node(self, signal_type, node_name):
        state = self._load_state()
        for pid in state['Nodes'][node_name]['pid']:
            os.kill(pid, int(signal_type))

    def stop(self, node_name):
        self._send_signal_to_node(signal.SIGTERM, node_name)

    def kill(self, node_name):
        self._send_signal_to_node(signal.SIGKILL, node_name)

    def get_node_names(self):
        state = self._load_state()
        return state['Nodes'].keys()

    def is_running(self, node_name):
        status = self._load_state()['Nodes'][node_name]['Status']
        return True if status == 'Running' else False

    def create_genesis_block(self, node_args):
        pass

    def _rm_wildcard(self, path, pattern):
        for each in os.listdir(path):
            if pattern.search(each):
                name = os.path.join(path, each)
                try:
                    os.remove(name)
                except PermissionError:
                    traceback.print_exc(file=sys.stderr)
                    sys.exit(1)
