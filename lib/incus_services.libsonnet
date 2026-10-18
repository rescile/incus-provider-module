// incus_services.libsonnet
{
  compute: {
    service: 'compute',
    decode_target: 'instances',
    components: {
      instance: 'instances',
      image: 'images',
      profile: 'profiles',
    },
    role: {
      name: 'compute-administrator',
      permissions: [
        'instances:read',
        'instances:create',
        'instances:update',
        'instances:delete',
        'instances:start',
        'instances:stop',
        'instances:restart',
        'instances:console',
        'instances:exec',
        'instances:snapshot',
        'instances:backup',
        'images:read',
        'profiles:read',
      ],
      description: 'Manage virtual-machine instances and their lifecycle. Limit access to authorized projects and prevent privileged host-level configuration.',
    },
  },

  container: {
    service: 'container',
    decode_target: 'instances',
    components: {
      instance: 'instances',
      image: 'images',
      profile: 'profiles',
    },
    role: {
      name: 'container-administrator',
      permissions: [
        'instances:read',
        'instances:create',
        'instances:update',
        'instances:delete',
        'instances:start',
        'instances:stop',
        'instances:restart',
        'instances:console',
        'instances:exec',
        'instances:snapshot',
        'instances:backup',
        'images:read',
        'profiles:read',
      ],
      description: 'Manage system-container instances. Enforce container-specific restrictions and prevent privileged host access.',
    },
  },

  storage: {
    service: 'storage',
    decode_target: 'storage_pools',
    components: {
      pool: 'storage_pools',
      volume: 'storage_volumes',
      bucket: 'storage_buckets',
    },
    role: {
      name: 'storage-administrator',
      permissions: [
        'storage_pools:read',
        'storage_volumes:read',
        'storage_volumes:create',
        'storage_volumes:update',
        'storage_volumes:delete',
        'storage_volumes:snapshot',
        'storage_volumes:backup',
        'storage_buckets:read',
        'storage_buckets:create',
        'storage_buckets:update',
        'storage_buckets:delete',
      ],
      description: 'Manage project-scoped storage volumes and buckets. Storage-pool creation and host-level storage administration require separate elevated privileges.',
    },
  },

  network: {
    service: 'network',
    decode_target: 'networks',
    components: {
      network: 'networks',
      forward: 'network_forwards',
      address_set: 'network_address_sets',
      integration: 'network_integrations',
    },
    role: {
      name: 'network-administrator',
      permissions: [
        'networks:read',
        'networks:create',
        'networks:update',
        'networks:delete',
        'network_forwards:read',
        'network_forwards:create',
        'network_forwards:update',
        'network_forwards:delete',
        'network_address_sets:read',
        'network_address_sets:create',
        'network_address_sets:update',
        'network_address_sets:delete',
      ],
      description: 'Manage permitted networks, forwards and address sets. Reserve uplinks, network integrations and cluster-wide changes for infrastructure administrators.',
    },
  },

  firewall: {
    service: 'firewall',
    decode_target: 'network_acls',
    components: {
      acl: 'network_acls',
      network: 'networks',
    },
    role: {
      name: 'firewall-administrator',
      permissions: [
        'network_acls:read',
        'network_acls:create',
        'network_acls:update',
        'network_acls:delete',
      ],
      description: 'Manage network ACL policies. ACL enforcement depends on the network driver and configuration.',
    },
  },

  load_balancer: {
    service: 'load_balancer',
    decode_target: 'network_load_balancers',
    components: {
      load_balancer: 'network_load_balancers',
      network: 'networks',
    },
    role: {
      name: 'load_balancer-administrator',
      permissions: [
        'network_load_balancers:read',
        'network_load_balancers:create',
        'network_load_balancers:update',
        'network_load_balancers:delete',
      ],
      description: 'Manage OVN network load balancers, listeners, backends and health checks. Requires a supported OVN network and authorized listen addresses.',
    },
  },

  dns: {
    service: 'dns',
    decode_target: 'network_zones',
    components: {
      zone: 'network_zones',
      record: 'network_zone_records',
    },
    role: {
      name: 'dns-administrator',
      permissions: [
        'network_zones:read',
        'network_zones:create',
        'network_zones:update',
        'network_zones:delete',
        'network_zone_records:read',
        'network_zone_records:create',
        'network_zone_records:update',
        'network_zone_records:delete',
      ],
      description: 'Manage Incus network zones and DNS records. Scope permissions to authorized projects and zones.',
    },
  },

  account: {
    service: 'account',
    decode_target: 'projects',
    components: {
      project: 'projects',
    },
    role: {
      name: 'project-administrator',
      permissions: [
        'projects:read',
        'projects:create',
        'projects:update',
        'projects:delete',
        'projects:configure',
      ],
      description: 'Manage project lifecycle and tenant configuration. Project creation, global configuration and authorization administration require appropriate server-level privileges.',
    },
  },

  audit: {
    service: 'audit',
    decode_target: 'instances',
    components: {
      instances: 'instances',
      projects: 'projects',
      networks: 'networks',
      storage: 'storage_pools',
      volumes: 'storage_volumes',
      images: 'images',
      profiles: 'profiles',
      zones: 'network_zones',
      acls: 'network_acls',
      certificates: 'certificates',
    },
    role: {
      name: 'auditor',
      permissions: [
        'instances:read',
        'projects:read',
        'networks:read',
        'storage_pools:read',
        'storage_volumes:read',
        'images:read',
        'profiles:read',
        'network_zones:read',
        'network_acls:read',
        'certificates:read',
        'operations:read',
        'events:read',
      ],
      description: 'Read-only infrastructure and configuration auditing. Do not grant console, exec, file access or secret-bearing workload access.',
    },
  },
}
