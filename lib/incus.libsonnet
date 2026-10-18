local portfolioData = import 'incus_services.libsonnet';

{
  title: 'Incus Provider Library',
  version: '0.0.1',
  name: 'incus',

  // Portfolio is represents keys of our portfolio data
  portfolio: std.objectFields(portfolioData),

  // Decode map dynamically derived from service decode_targets + component maps
  decode: {
    // 1. Service-level decode targets
    [svcKey]: portfolioData[svcKey].decode_target
    for svcKey in std.objectFields(portfolioData)
  } + {
    // 2. Automatically extract component maps from each service role
    [compKey]: portfolioData[svcKey].role.component[compKey]
    for svcKey in std.objectFields(portfolioData)
    for compKey in (
      local role = std.get(portfolioData[svcKey], 'role', null);
      if role != null && std.objectHas(role, 'component') && role.component != null
      then std.objectFields(role.component)
      else []
    )
  } + {
  // 3. Fallbacks or manual extra decodes
  cluster_member: 'cluster_members',
  certificate: 'certificates',
  operation: 'operations',
  event: 'events',
  },

  // Safely resolve a decoder key
  getResource(key, default=''):: std.get(self.decode, key, default),

  // Roles map fixed to correctly extract the role object
  roles: {
    [portfolioData[svcKey].role.name]: portfolioData[svcKey].role
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
