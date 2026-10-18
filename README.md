# Incus Provider Module

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Rescile UCS](https://img.shields.io/badge/provisioned%20by-Rescile%20UCS-purple.svg)](https://www.rescile.com/)
[![Contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](CONTRIBUTING.md)

This module creates and configures an **Incus Project** as a managed infrastructure target for subsequent resource deployments. It provides the foundation on which additional Incus resources can be provisioned, connected and managed through the Rescile UCS infrastructure model. The goal is to establish a simple, reusable and community-extensible resource model for Incus infrastructure.

## Rescile UCS

The module serves as  part of the **Rescile UCS infrastructure ecosystem**. Rescile UCS acts as the provisioning and orchestration environment. It maintains the infrastructure model, resolves dependencies and drives the execution of infrastructure changes. The relationship can be summarized as:

```text
┌──────────────────────────────┐
│         Rescile UCS          │
│                              │
│   Model → Resolve → Deploy   │
└───────────────┬──────────────┘
                │
                ▼
┌──────────────────────────────┐
│      Landing Zone Module     │
│                              │
│                              │
└───────────────┬──────────────┘
                │
                ▼
┌──────────────────────────────┐
│     Incus Provider Module    │
│                              │
│                              │
│  Incus.json                  │
└──────────────────────────────┘
```

UCS provides the common control plane, while individual modules describe the infrastructure resources that can be provisioned. This separation allows modules to remain focused on **what infrastructure should exist**, while UCS manages **how infrastructure is modeled, related and provisioned**. For more information, see the [Rescile UCS project](https://www.rescile.com/).

## Dependencies

| Module              | Resource                                                                  |
| ------------------- | ------------------------------------------------------------ |
| core                | The UCS core defines the `resident.toml` that holds together multiple subscriptions |
| landing zone        | The landing zone introduces a `subscription.toml` that serves as root for Incus resouce definitions. |

The resource catalog is intentionally small at this stage. Additional Incus resources are expected to be contributed by the community.

## Example

A minimal configuration can extend an Incus blueprint as follows:

```toml
origin_resource = "network"

[create_resouce]
name = "load_balancer-service"
```

The module is used by Rescile UCS to define subsequent infrastructure resources at Incus.

For example:

```text
Incus Project
    │
    ├── Network
    │    ├── ACL
    │    └── zone
    │
    ├── Instance
    │
    ├── Load-Balancer
    │
    └── ...
```

## Repository Structure

```text
.
├── README.md
├── LICENSE
├── NOTICE
├── CONTRIBUTING.md
├── module.toml
├── input/
│    └── incus.libsonnet
│ 
└── output/
     └── ...
```

The exact structure may evolve as additional resources are introduced. The intention is to keep resources independently understandable and make it straightforward for contributors to add new Incus capabilities.

## Contributing

**Contributions are welcome.**

This project is intended to grow beyond the initial Incus Region resource through contributions from infrastructure engineers, cloud architects and the wider Rescile community.

Useful contributions include:

* Resource schema improvements
* Incus capability coverage
* Dependency definitions
* Validation and testing
* Documentation and examples
* Bug fixes
* Improvements to the Rescile UCS integration
* Real-world deployment examples

### Contribution Workflow

1. **Open an issue**: Describe the resource or improvement you would like to contribute.
2. **Discuss the design**: For new resources, agree on the resource model, attributes and dependencies before implementing larger changes.
3. **Fork the repository**: Create your own fork and work in a dedicated branch.
4. **Implement the change**: Follow the existing resource structure and include tests and documentation where appropriate.
5. **Submit a pull request**: Clearly describe what has changed and why.
6. **Review**: Maintainers and community members review the implementation, resource model and compatibility with Rescile UCS.
7. **Merge**: Once approved, the contribution becomes part of the shared module ecosystem.

### Adding a New Resource

A typical contribution should include:

```text
input/
└── ...

output/
└── ...
```

Contributors should avoid introducing provider-specific assumptions where the resource can be expressed through the common Rescile UCS infrastructure model.

* **Design Principles**: The module follows a few basic principles:
* **Declarative**: Resources describe the desired infrastructure state rather than prescribing an imperative sequence of operations.
* **Composable**: Resources should be usable as building blocks for larger infrastructure configurations.
* **Dependency-aware**: Relationships between resources should be explicitly represented so that Rescile UCS can construct and evaluate the resulting infrastructure dependency graph.
* **Cloud-native**: The module should expose Incus capabilities without unnecessarily hiding important Incus-specific configuration.
* **Community-driven**: The resource catalog should evolve based on real-world requirements and contributions from the community.

## License

This project is licensed under the *Apache License 2.0*. The Apache-2.0 license is a permissive open-source license that allows use, modification and redistribution while providing an explicit patent license to contributors. See [`LICENSE`](LICENSE) for the complete license text. Unless required by applicable law or agreed to in writing, software distributed under this license is provided **"AS IS"**, without warranties or conditions of any kind.

## Copyright

Copyright © Rescile GmbH

Contributions are accepted under the terms of the Apache License 2.0.

---

**Build infrastructure together.**

If you have an Incus resource that should be available through the Rescile UCS ecosystem, contributions are welcome.
