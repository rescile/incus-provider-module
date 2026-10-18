local portfolioData = import 'incus_services.libsonnet';

{
  title: 'Incus Provider Library',
  version: '0.0.1',
  name: 'incus',

  // Portfolio is represents keys of our portfolio data
  portfolio: std.objectFields(portfolioData),

  // Decode map is dynamically derived from each service's decode_target + component maps
  decode: {
    [svcKey]: portfolioData[svcKey].decode_target
    for svcKey in std.objectFields(portfolioData)
  } + {
    cluster_member: 'cluster_members',
    certificate: 'certificates',
    operation: 'operations',
    event: 'events',
  },

  // Safely resolve a decoder key
  getResource(key, default=''):: std.get(self.decode, key, default),

  // Roles map is derived from each service's role definition
  roles: {
    [portfolioData[svcKey].role.name]: portfolioData[svcKey] {
      // Clean up the role object structure for consumers
      role:: null,
    }.role
    for svcKey in std.objectFields(portfolioData)
  },

  // Helper functions
  // Get a specific role object safely
  getRole(roleName)::
    if std.objectHas(self.roles, roleName) then
      self.roles[roleName]
    else
      error "Role '" + roleName + "' does not exist in Incus provider.",

  // Get all role keys associated with a service domain
  getServiceRoles(serviceName):: [
    roleKey
    for roleKey in std.objectFields(self.roles)
    if std.get(self.roles[roleKey], 'service') == serviceName
  ],

  // Retrieve deduplicated permissions by service name
  getAdminPermissions(serviceName)::
    local matchingPermissions = [
      perm
      for roleKey in self.getServiceRoles(serviceName)
      for perm in std.get(self.roles[roleKey], 'permissions', default=[])
    ];
    std.set(matchingPermissions),

  // Resolve a shorthand component key to its API endpoint
  resolveComponent(serviceName, componentKey)::
    local roleKeys = self.getServiceRoles(serviceName);
    local found = [
      self.roles[rk].component[componentKey]
      for rk in roleKeys
      if std.objectHas(self.roles[rk], 'component') && std.objectHas(self.roles[rk].component, componentKey)
    ];
    if std.length(found) > 0 then found[0] else error ("Component '" + componentKey + "' not found for service '" + serviceName + "'"),

  // Derive a custom role extended with extra permissions
  deriveRoleWithOverrides(roleName, extraPermissions)::
    local baseRole = self.getRole(roleName);
    baseRole {
      permissions: std.set(baseRole.permissions + extraPermissions),
    },

  // Generate standardized definition stubs for all portfolio domains
  generatePortfolioDefinitions():: {
    [serviceName]: {
      meta: {
        provider: self.name,
        version: self.version,
        service: serviceName,
      },
      associated_roles: self.getServiceRoles(serviceName),
      permissions: self.getAdminPermissions(serviceName),
    }
    for serviceName in self.portfolio
  },
}
