"""
Contains class used to install and manage a Chorus installation
"""

import os
from library import utilities
from resource_management import check_process_status
from resource_management.core.exceptions import ComponentIsNotRunning

class Chorus(object):
    """
    Manage a Chorus installation
    """

    _accountName = "chorus"
    _account = None

    def __init__(self, params):
        self.params = params

    def user(self):
        """
        Create a chorus user if it doesn't exist, and
        return the user's uid and gid.
        """

        if self._account == None:
            self._account = utilities.create_user(self._accountName)

        return self._account

    def create_directory(self, directory):
        """
        Create a directory with the chorus user as owner and group.
        """

        user = self.user()
        os.makedirs(directory)
        os.chown(directory, user['uid'], user['gid'])

    def install(self):
        """
        Prepare and install Chorus onto the system via a given self extracting shell script.
        """

        self.configure()

        try:
            install_output = utilities.run(
                "/usr/bin/env bash %s" % self.params.installerPath,
                communicate=self._build_installation_parameters(),
                user=self.user()
            )
        except Exception as exception:
            raise Exception("There were errors during the installation: %s" % exception)

        if install_output.find("An error has occurred. Trying to back out and restore previous state") != -1:
            with open(os.path.join(self.params.installationDirectory, 'install.log'), 'r') as filehandle:
                raise Exception("The installation encountered an error and attempted to roll back: %s" % filehandle.read())

        return install_output

    def _build_installation_parameters(self):
        """
        Create the string passed to the self extracting installation script to install Chorus.
        """

        installation_options = []

        # Terms accepted
        installation_options.append('y' if self.params.termsAccepted else 'n')

        # Installation Directory
        if not os.path.exists(self.params.installationDirectory):
            raise AttributeError("Installation directory '%s' does not exist." % self.params.installationDirectory)

        installation_options.append(self.params.installationDirectory)

        # Data directory
        if not os.path.exists(self.params.dataDirectory):
            raise AttributeError("Data directory '%s' does not exist." % self.params.dataDirectory)

        installation_options.append(self.params.dataDirectory)

        # Salt
        installation_options.append(self.params.securitySalt)

        return "\n".join(installation_options) + "\n"

    def configure(self):
        """
        Prepare the system for Chorus to be installed.
        """

        if not os.path.exists(self.params.installationDirectory):
            self.create_directory(self.params.installationDirectory)

        if not os.path.exists(self.params.dataDirectory):
            self.create_directory(self.params.dataDirectory)

        ## More configurations here in the future

    def start(self):
        """
        Start Chorus as the chorus user using chorus_control.sh
        """

        print utilities.run(os.path.join("source " + self.params.installationDirectory, "chorus_path.sh") + " && chorus_control.sh start", communicate="", user=self.user())

    def stop(self):
        """
        Stop Chorus as the chorus user using chorus_control.sh
        """

        print utilities.run(os.path.join("source " + self.params.installationDirectory, "chorus_path.sh") + " && chorus_control.sh stop", communicate="", user=self.user())

    def is_running(self):
        """
        Check if Chorus is running by verifying the processes using their various pid files.
        """

        pid_files = {
            'solr': os.path.join(self.params.installationDirectory, "tmp/pids/solr-production.pid"),
            'nginx': os.path.join(self.params.installationDirectory, "tmp/pids/nginx.pid"),
            'jetty': os.path.join(self.params.installationDirectory, "tmp/pids/jetty.pid"),
            'schedulrer': os.path.join(self.params.installationDirectory, "tmp/pids/scheduler.production.pid"),
            'worker': os.path.join(self.params.installationDirectory, "tmp/pids/worker.production.pid"),
            'mizuno': os.path.join(self.params.installationDirectory, "tmp/pids/mizuno.pid"),
            'postgres': os.path.join(self.params.installationDirectory, "postgres-db/postmaster.pid")
        }

        not_running = []

        for process, pid in pid_files.iteritems():
            try:
                check_process_status(pid)
            except ComponentIsNotRunning:
                not_running.append(process)

        if len(not_running) > 0:
            raise ComponentIsNotRunning("\n".join(not_running) + " aren't currently running")
