#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module to set common arguments used by all platforms, and import Arguments for each platform and modules
"""
import argparse
import re
import importlib
import sys
from libs.elasticsearch import ElasticArguments
from libs.logging import LoggingArguments


class Arguments(argparse.ArgumentParser):
    """Common Arguments and imports for logging and elasticsearch arguments"""

    def __init__(self, environment):
        super().__init__()
        EnvDefault = self.EnvDefault

        self.common_parser = argparse.ArgumentParser(description="Common Arguments", add_help=False)

        self.common_parser.add_argument("--platform", action=EnvDefault, env=environment, envvar="ROSA_BURNER_PLATFORM", required=True, choices=["rosa"])
        self.common_parser.add_argument("--subplatform", action=EnvDefault, env=environment, envvar="ROSA_BURNER_SUBPLATFORM", help="Subplatforms of Platform", required=False)

        self.common_parser.add_argument("--uuid", action=EnvDefault, env=environment, envvar="ROSA_BURNER_UUID", required=False)
        self.common_parser.add_argument("--path", action=EnvDefault, env=environment, envvar="ROSA_BURNER_PATH", required=False)

        self.common_parser.add_argument("--cluster-name-seed", action=EnvDefault, env=environment, envvar="ROSA_BURNER_CLUSTER_NAME_SEED", type=str, default="perfsc", help="Seed used to generate cluster names. 6 chars max")

        self.common_parser.add_argument("--workers", action=EnvDefault, env=environment, envvar="ROSA_BURNER_WORKERS", type=self._verify_workers, required=True, default="3",
                                        help="Number of workers for the hosted cluster (min: 3). If list (comma separated), iteration over the list until reach number of clusters")
        self.common_parser.add_argument("--workers-wait-time", type=int, default=60, action=EnvDefault, env=environment, envvar="ROSA_BURNER_WORKERS_WAIT_TIME",
                                        help="Waiting time in minutes for the workers to be Ready after cluster installation or machinepool creation . If 0, do not wait. Default: 60 minutes")
        self.common_parser.add_argument("--wait-for-workers", action="store_true", help="After cluster will be ready, wait for all workers to be also ready", required=False)

        self.common_parser.add_argument("--cluster-count", action=EnvDefault, env=environment, envvar="ROSA_BURNER_CLUSTER_COUNT", type=int, default=1)
        self.common_parser.add_argument("--delay-between-batch", action=EnvDefault, env=environment, envvar="ROSA_BURNER_DELAY_BETWEEN_BATCH", default=60, type=int,
                                        help="If set it will wait x seconds between each batch request", required=False)
        self.common_parser.add_argument("--batch-size", action=EnvDefault, env=environment, envvar="ROSA_BURNER_BATCH_SIZE", type=int, default=0, help="number of clusters in a batch", required=False)

        self.common_parser.add_argument("--watcher-delay", action=EnvDefault, env=environment, envvar="ROSA_BURNER_WATCHER_DELAY", default=60, type=int, help="Delay between each status check")

        self.common_parser.add_argument("--wildcard-options", action=EnvDefault, env=environment, envvar="ROSA_BURNER_WILDCARD_OPTIONS", help="String to be passed directly to cluster create command on any platform. It wont be validated", required=False)

        self.common_parser.add_argument("--enable-workload", action="store_true", help="Execute workload after clusters are installed", required=False)
        self.common_parser.add_argument("--workload-repo", action=EnvDefault, env=environment, envvar="ROSA_BURNER_WORKLOAD_REPO", default="https://github.com/cloud-bulldozer/e2e-benchmarking.git", type=str, help="Git Repo of the workload", required=False)
        self.common_parser.add_argument("--workload", action=EnvDefault, env=environment, envvar="ROSA_BURNER_WORKLOAD", help="Workload to execute after clusters are installed", default="cluster-density-ms")
        self.common_parser.add_argument("--workload-script", action=EnvDefault, env=environment, envvar="ROSA_BURNER_WORKLOAD_SCRIPT", help="Workload to execute after clusters are installed", default="workloads/kube-burner-ocp-wrapper/run.sh")
        self.common_parser.add_argument("--workload-executor", action=EnvDefault, env=environment, envvar="ROSA_BURNER_WORKLOAD_EXECUTOR", help="Complete path of binary used to execute the workload", default="/usr/bin/kube-burner")
        self.common_parser.add_argument("--workload-duration", action=EnvDefault, env=environment, envvar="ROSA_BURNER_WORKLOAD_DURATION", default="1h", type=str, help="Workload execution duration in minutes", required=False)
        self.common_parser.add_argument("--workload-jobs", action=EnvDefault, env=environment, envvar="ROSA_BURNER_WORKLOAD_JOBS", type=int, default=10, help="Jobs per worker.Workload will scale this number to the number of workers of the cluster", required=False)

        self.common_parser.add_argument("--cleanup-clusters", action="store_true", help="Delete all created clusters at the end", required=False)
        self.common_parser.add_argument("--wait-before-cleanup", action=EnvDefault, env=environment, envvar="ROSA_BURNER_WAIT_BEFORE_CLEANUP", help="Minutes to wait before starting the cleanup process", default=0, type=int, required=False)
        self.common_parser.add_argument("--delay-between-cleanup", action=EnvDefault, env=environment, envvar="ROSA_BURNER_DELAY_BETWEEN_CLEANUP", help="Minutes to wait between cluster deletion", default=0, type=int, required=False)

        self.common_args, self.unknown_args = self.common_parser.parse_known_args()

        log_parser = argparse.ArgumentParser(description="Logging Arguments", add_help=False)
        LoggingArguments(log_parser, environment)

        es_parser = argparse.ArgumentParser(description="ElasticSearch Arguments", add_help=False)
        ElasticArguments(es_parser, environment)

        try:
            if self.common_args.subplatform:
                platform_module_path = "libs.platforms." + self.common_args.platform + "." + self.common_args.subplatform + "." + self.common_args.subplatform
                platform_module = importlib.import_module(platform_module_path)
                platformarguments = getattr(platform_module, self.common_args.subplatform.capitalize() + "Arguments")
            else:
                platform_module_path = "libs.platforms." + self.common_args.platform + "." + self.common_args.platform
                platform_module = importlib.import_module(platform_module_path)
                platformarguments = getattr(platform_module, self.common_args.platform.capitalize() + "Arguments")
            platform_parser = argparse.ArgumentParser(description="Platform Arguments", add_help=False)
            platformarguments(platform_parser, environment)
        except ImportError as err:
            print(err)
            sys.exit("Exiting...")
        except AttributeError as err:
            print(err)
            sys.exit("Exiting...")

        self.parser = argparse.ArgumentParser(
            description="Rosa-Burner",
            add_help=True,
            parents=[
                self.common_parser,
                log_parser,
                es_parser,
                platform_parser,
            ]
        )
        self.parameters = vars(self.parser.parse_args())

    def __getitem__(self, item):
        return self.parameters[item] if item in self.parameters else None

    def _verify_workers(self, workers):
        pattern = re.compile(r"^(\d+)(,\s*\d+)*$")
        if workers.isdigit() and int(workers) % 3 != 0:
            self.common_parser.error(f"Invalid value ({workers}) for parameter  `--workers`. If digit, it must be divisible by 3'")
        elif bool(pattern.match(workers)):
            for num in workers.split(","):
                if int(num) < 3 or int(num) % 3 != 0:
                    self.common_parser.error(f"Invalid value ({num}) for parameter `--workers`. If list, all values must be divisible by 3")
        return workers

    # def set_common_defaults(self):
    #     """"""
    #     common_defaults = vars(self.parser.parse_args([]))
    #     for subparser in [self.rosa_parser, self.hypershift_parser]:
    #         subparser.set_defaults(**common_defaults)

    class EnvDefault(argparse.Action):
        """Argument passed has preference over the envvar"""

        def __init__(self, env, envvar, required=True, default=None, **kwargs):
            if not default and envvar:
                if envvar in env:
                    default = env[envvar]
            if required and default:
                required = False
            super(Arguments.EnvDefault, self).__init__(
                default=default, required=required, **kwargs
            )

        def __call__(self, parser, namespace, values, option_string=None):
            setattr(namespace, self.dest, values)