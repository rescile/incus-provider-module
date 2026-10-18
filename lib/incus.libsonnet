// incus.libsonnet
{
  title: 'Incus Provider Library',
  version: '0.0.1',
  name: 'incus',
  decode: {
    // Access and tenancy
    account: 'project',
    subscription: 'cluster',

    // Connectivity and networking
    dns: 'zone',
    firewall: 'acl',
    network: 'network',

    // Compute and orchestration
    compute: 'instances',

    // Storage and data services
    storage: 'storage_pools',

    // Incus-specific resources
    cluster_member: 'cluster_members',
    image: 'images',
    instance: 'instances',
    network_acl: 'network_acls',
    network_zone: 'network_zones',
    profile: 'profiles',
    project: 'projects',
    storage_bucket: 'storage_buckets',
    storage_volume: 'storage_volumes',
    certificate: 'certificates',
  },
  region: {},
  portfolio: [
    'container',
    'compute',
    'dns',
    'firewall',
    'load_balancer',
    'network',
    'storage',
  ],
  roles: {
    'compute-administrator': {
      service: 'compute',
      component: {
        instance: 'instances',
        image: 'images',
        profile: 'profiles',
      },
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

    'container-administrator': {
      service: 'container',
      component: {
        instance: 'instances',
        image: 'images',
        profile: 'profiles',
      },
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

    'storage-administrator': {
      service: 'storage',
      component: {
        pool: 'storage_pools',
        volume: 'storage_volumes',
        bucket: 'storage_buckets',
      },
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

    'network-administrator': {
      service: 'network',
      component: {
        network: 'networks',
        forward: 'network_forwards',
        address_set: 'network_address_sets',
        integration: 'network_integrations',
      },
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

    'firewall-administrator': {
      service: 'firewall',
      component: {
        acl: 'network_acls',
        network: 'networks',
      },
      permissions: [
        'network_acls:read',
        'network_acls:create',
        'network_acls:update',
        'network_acls:delete',
      ],
      description: 'Manage network ACL policies. ACL enforcement depends on the network driver and configuration.',
    },

    'load_balancer-administrator': {
      service: 'load_balancer',
      component: {
        load_balancer: 'network_load_balancers',
        network: 'networks',
      },
      permissions: [
        'network_load_balancers:read',
        'network_load_balancers:create',
        'network_load_balancers:update',
        'network_load_balancers:delete',
      ],
      description: 'Manage OVN network load balancers, listeners, backends and health checks. Requires a supported OVN network and authorized listen addresses.',
    },

    'dns-administrator': {
      service: 'dns',
      component: {
        zone: 'network_zones',
        record: 'network_zone_records',
      },
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

    'project-administrator': {
      service: 'account',
      component: {
        project: 'projects',
      },
      permissions: [
        'projects:read',
        'projects:create',
        'projects:update',
        'projects:delete',
        'projects:configure',
      ],
      description: 'Manage project lifecycle and tenant configuration. Project creation, global configuration and authorization administration require appropriate server-level privileges.',
    },

    auditor: {
      service: 'audit',
      component: {
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

  // Retrieve deduplicated permissions by service name
  getAdminPermissions(serviceName)::
    local matchingPermissions = [
      perm
      for roleKey in std.objectFields(self.roles)
      if std.get(self.roles[roleKey], 'service') == serviceName
      for perm in std.get(self.roles[roleKey], 'permissions', default=[])
    ];
    std.set(matchingPermissions),
}
