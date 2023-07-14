# Welcome to flamelet

For full documentation visit [flamelet.org](https://www.flamelet.org).

## Commands

* `flamelet new [dir-name]` - Create a new project.
* `flamelet serve` - Start the live-reloading docs server.
* `flamelet build` - Build the documentation site.
* `flamelet -h` - Print help message and exit.

## Project layout

    flamelet.yml    # The configuration file.
    docs/
        index.md  # The documentation homepage.
        ...       # Other markdown pages, images and other files.


## What is Flamelet?
Flamelet is a DevOps tool for remote infrastructure management.
With Flamelet you can provision and update ...
Everything necessary for provisioning new infrastructure is already included in Flamelet. Furthermore functionality can be easily added with ...

## Use Cases
Provisioning new infrastructure remotely. Be it servers, including setting up users, sudo, shell, ...
Operating systems on computers, servers, 

## Prerequisites
- A Unix-like operating system: macOS, Linux, BSD. On Windows: WSL2 is preferred, but cygwin or msys also mostly work.
- `bash` should be installed
- `curl` or `wget` should be installed
- `git` should be installed


## Installation
Flamelet is installed by running one of the following commands in your terminal. You can install this via the command-line with either `curl`, `wget` or another similar tool.

| Method        | Command                                                                                               |
| :------------ | :---------------------------------------------------------------------------------------------------- |
| **curl**      | `sh -c "$(curl -fsSL https://raw.githubusercontent.com/flameletlabs/flamelet/main/tools/install.sh)"` |
| **wget**      | `sh -c "$(wget -O- https://raw.githubusercontent.com/flameletlabs/flamelet/main/tools/install.sh)"`   |
| **fetch**     | `sh -c "$(fetch -o - https://raw.githubusercontent.com/flameletlabs/flamelet/main/tools/install.sh)"` |

## First Run


## Examples

## Adding Roles for further functionality


### Source of adding new roles
Ansible Galaxy prodes a vast amount of roles which can be integrated into Flamelet to extend its functionality. Simply go to https://galaxy.ansible.com/, filter for "Roles" and look for what you need.

## Updating Flamelet

## Deleting Flamelet