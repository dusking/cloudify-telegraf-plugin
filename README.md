**WIP**

cloudify-telegraf-plugin
========================

* Master Branch [![CircleCI](https://circleci.com/gh/cloudify-cosmo/cloudify-telegraf-monitoring-plugin.svg?style=svg)](https://circleci.com/gh/cloudify-cosmo/cloudify-telegraf-monitoring-plugin)

## Description

cloudify-telegraf-plugin is used to install & configure [Telegraf](https://influxdata.com/time-series-platform/telegraf/) monitoring agent on hosts.
Telgraf agent allows to collect time-series data from variety of sources ([inputs](https://docs.influxdata.com/telegraf/v1.4/inputs/)) and send them to desired destination ([outputs](https://docs.influxdata.com/telegraf/v1.4/outputs/)).

## Usage
cloudify-telegraf-plugin usage is very simple and require no more than config parameters as inputs. 
for each node which required telegraf agent - just enable the "monitoring agent" under the 'interface' section and provide the desired inputs. for example:

```yaml
VM:
    type: cloudify.openstack.nodes.Server
    properties:
      resource_id:
      cloudify_agent:
    interfaces:
      cloudify.interfaces.monitoring_agent:
        install:
          implementation: telegraf.cloudify_telegraf.tasks.install
          inputs:
            download_url:
            config_file:
            config_inputs:
              agent_logfile: /var/log/telegraf.log
              global_tags:
                deployment: CTX_DEPLOYMENT_ID
                tenant: CTX_TENANT_NAME
                user: me
              outputs:
                influxdb:
                  urls:
                    - http://10.239.2.115:8086
                  database: telegraf
              inputs:
                mem:
                processes:
                swap:
                system:
                cpu:
                  percpu: false
                  totalcpu: true
                  collect_cpu_time: false
                disk:
                  ignore_fs:
                    - tmpfs
                    - devtmpfs
                    - devfs
        start:
            implementation: telegraf.telegraf_plugin.tasks.start
```
As you can see, in order to add telegraf to node - we provided 'config_inputs' which is a dict with the following mandatory sub-dicts:
* **inputs**
* **outputs**

during the plugin installation process, a valid config file is generated - base on the inputs which provided.

Another option is to provide a ready and valid configuration file under 'telegraf_config_file' input (by default, this input is None).

> Notice! in order to provide valid inputs\config file, follow the [configuration editting instructions.](https://docs.influxdata.com/telegraf/v0.13/introduction/getting_started/#configuration)

Two additional inputs are:
* **telegraf_install_path** - sets the directory which thw system will be downloaded and install in (by default - set to be: /opt/telegraf)
* **download_url** - sets the url which telegraf will be downloaded from (by defaults - set to be from http://get.influxdb.org/telegraf, version 0.12.0)



