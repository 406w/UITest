#!/bin/sh
set -eu
export JENKINS_SECRET="$(cat /run/secrets/jenkins_agent_secret)"
exec /usr/local/bin/jenkins-agent "$@"
