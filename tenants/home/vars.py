"""flamelet-home variables: SSH keys, passwords, user configs."""

from core.operations.users import BASH, SUDO_GROUP

# System groups to create (detail provided by tenant, not framework)
GROUPS = ["syseng", "keep"]

# Password for all shell users: lumaca (sha-512)
LUMACA_PASSWORD = "$6$wYAAqocjxEIwdjv6$FFWYwiO6sG6.GW1g0pD52bHMVvEJgyS93.o3fQrYSIAVm0CtTpc1gaosdiWDyYSnrDcPpk9tVBSVQJow2VzCZ0"

# SSH keys per user
SYSENG_SSH_KEYS = [
    "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDe+mwkGr0m67TsmY2Lv1AvSHMnhNx+GGBZKbFAo9FXaaYPbEUNSS13Ic5V/X8i/ifzcO9wTX3+TJE/++zrQ/qVvR+WmgksWF1gzAkdf2SyxEx5VsP7/WG/I4Ja7DKZD5Y/w5G9bzLOok5nymQYzodU8oUNEG+txLWK4GUsRZfSLfFVUNvIdHqbFKZZqFyjGRllazBxa+jxUjlA7U1Xy2pq4o+HGgW3GTuw7fz3MdmYoI/r30jDWarKKWdynFCqNHkTOUEyJRcur37AiV4jqUlbdGzVTGn0P+o2HfkRNjsCdD2yi4JLPaWHixsCNAuxZE6S7O7gT+DbfgeLK86H2vx7 syseng@vault.lan",
    "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDn2DDRyv1dV/c4OeHOUjSqbKW781uHi8z+945QuJoLJNgy5W0jDG6YynYcaIN1jtkMg1wrfvrsy5BsMolaR9BHHgSTOnj19NmV6y26NwMSRzq/XvSSYVqacOC90cNU/xKY50K/UJnns3C87nxKCdQeLAHfw/ONmHW/8dAKB4OK/6thIUXWPWU1+bVnkN1SGduon9vvWgB5/0d750b8HH0jEbiBvxOyYJhGvLKtCWI0vWHFpFWnxF2IccxXR+2kwt2sTWHOfYaTVPvXaNkyJus+71DJ+9GwNCcfwGeVBbRTTqgVK+5ZT+zTDdlz7+FFRoxReErpz0oDxNjn4jktznSD eim@avalanche-2048",
]

KEEP_SSH_KEYS = [
    "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQC4Bk95HCQODHqKD8VQb7tl5KJ1p6t54lJfYndX8E9aQAfV7OwQgTgyRo5peDUo+iuBHl37ncNvLSj56kFoeaSjK0br7R37JCWA1/NDyMlOeeH7qQMjpIwhexAjmzHT3inCGWtNjQz8IGG1drKRTICactkwdAa/Xd9TmMjZA+5rsRhZbFbWS5h1pbKtEVEBArdJYKZC9P5hFhKWfuGIwE/fHAWsvljNDbhcu4ZZ74N4t8zTEq2+V929esmVv0vf0NSYpcqZXoENU5eD2X+k9sCbTVpBHmgHSfMyYKi4FPvrBTBVi7miWmBMHM1CSAPSmBvy3DKODUPqxko3UCplSD+LOKfCf1VrfpJQOk7WGvAkR3LRQoaoqbgfRnaP6THstxu6InLOa9Qq82NoWCm/CsptcmcmJFO4cI81HYwCRYsoTir58FjI9tN880PcAHLxEdttp/JH2IadkGVuu7O4B2FYUo1+QaFQV9Uz3OKXBZ3n7HjGNdjUhESAgawcY4gfCfn1aPjkJn+G/86Av7R6v490ogVFTIBHGCOSNs9W5SH+PqqE5kgVtHxnW9Z7kG+KEd67sLrqm30sQt2olVrgJMsNtE2W4Hy8phGyKnkV1t/Re/78a9+xqKUksWtecUECApC0bUikmHyFtNGsBet3DsOznFaWOEBdcB42w2Nqxr1geQ== keep@home",
]

# User configurations
USERS = {
    "syseng": {
        "comment": "System Engineering",
        "password": LUMACA_PASSWORD,
        "groups": SUDO_GROUP,  # Dict will be resolved per-host by add_users
        "shell": BASH,         # Dict will be resolved per-host by add_users
        "public_keys": SYSENG_SSH_KEYS,
    },
    "keep": {
        "comment": "Backup User",
        "password": LUMACA_PASSWORD,
        "groups": [],
        "shell": "/bin/sh",
        "public_keys": KEEP_SSH_KEYS,
    },
}
