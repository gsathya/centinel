#!/usr/bin/python
# Ben Jones bjones99@gatech.edu
# Georgia Tech Fall 2014
#
# vpn.py: a top level interface to commands to run VPNs on a VM as
# different clients. The use case is allowing us to measure from more
# places.

import argparse
import os

import centinel.backend
import centinel.client
import centinel.config
import centinel.openvpn
import centinel.hma


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--auth-file', '-u', dest='authFile',
                        help=("File with HMA username on first line, \n"
                              "HMA password on second line"))
    parser.add_argument('--create-hma-configs', dest='createHMA',
                        action="store_true",
                        help='Create the openvpn config files for HMA')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--directory", "-d", dest='directory',
                       help="Directory with experiments, config files, etc.")
    create_conf_help = ("Create configuration files for the given "
                        "openvpn config files so that we can treat each "
                        "one as a client. The argument should be a "
                        "directory with a subdirectory called openvpn "
                        "that contains the openvpn config files")
    group.add_argument('--create-config', '-c', help=create_conf_help,
                       dest='createConfDir')
    return parser.parse_args()


def scan_vpns(directory, auth_file):
    """For each VPN, check if there are experiments and scan with it if
    necessary

    Note: the expected directory structure is
    args.directory
    -----vpns (contains the OpenVPN config files
    -----configs (contains the Centinel config files)
    -----exps (contains the experiments directories)

    """

    # iterate over each VPN
    vpn_dir = return_abs_path(directory, "vpns")
    conf_dir = return_abs_path(directory, "configs")
    auth_file = return_abs_path(".", auth_file)
    for filename in os.listdir(conf_dir):
        vpn_config = os.path.join(vpn_dir, filename)
        cent_config = os.path.join(conf_dir, filename)
        vpn = centinel.openvpn.OpenVPN(timeout=30, auth_file=auth_file,
                                       config_file=vpn_config)
        vpn.start()
        if not vpn.started:
            vpn.stop()
            continue
        # now that the VPN is started, get centinel to process the VPN
        # stuff and sync the results
        config = centinel.config.Configuration()
        config.parse_config(cent_config)
        client = centinel.client.Client(config.params)
        client.setup_logging()
        client.run()
        centinel.backend.sync(config.params)
        vpn.stop()

def return_abs_path(directory, path):
    """Unfortunately, Python is not smart enough to return an absolute
    path with tilde expansion, so I writing functionality to do this

    """
    if directory is None or path is None:
        return
    directory = os.path.expanduser(directory)
    return os.path.abspath(os.path.join(directory, path))

def create_config_files(directory):

    """For each VPN file in directory/vpns, create a new configuration
    file and all the associated directories

    Note: the expected directory structure is
    args.directory
    -----vpns (contains the OpenVPN config files
    -----configs (contains the Centinel config files)
    -----exps (contains the experiments directories)
    -----results (contains the results)

    """
    vpn_dir = return_abs_path(directory, "vpns")
    conf_dir = return_abs_path(directory, "configs")
    os.mkdir(conf_dir)
    home_dirs = return_abs_path(directory, "home")
    os.mkdir(home_dirs)
    for filename in os.listdir(vpn_dir):
        configuration = centinel.config.Configuration()
        # setup the directories
        home_dir = os.path.join(home_dirs, filename)
        os.mkdir(home_dir)
        configuration.params['user']['centinel_home'] = home_dir
        exp_dir = os.path.join(home_dir, "experiments")
        os.mkdir(exp_dir)
        configuration.params['dirs']['experiments_dir'] = exp_dir
        data_dir = os.path.join(home_dir, "data")
        os.mkdir(data_dir)
        configuration.params['dirs']['data_dir'] = data_dir
        res_dir = os.path.join(home_dir, "results")
        os.mkdir(res_dir)
        configuration.params['dirs']['results_dir'] = res_dir

        log_file = os.path.join(home_dir, "centinel.log")
        configuration.params['log']['log_file'] = log_file
        login_file = os.path.join(home_dir, "login")
        configuration.params['server']['login_file'] = login_file

        conf_file = os.path.join(conf_dir, filename)
        configuration.write_out_config(conf_file)


if __name__ == "__main__":
    args = parse_args()

    if args.createConfDir:
        if args.createHMA:
            hmaDir = return_abs_path(args.createConfDir, "vpns")
            centinel.hma.create_config_files(hmaDir)
        # create the config files for the openvpn config files
        create_config_files(args.createConfDir)
    else:
        scan_vpns(args.directory, args.authfile)
