import { Stack, StackProps, Tags } from "aws-cdk-lib";
import { Construct } from "constructs";

interface ContainerRegistryStackProps extends StackProps {
  applicationName: string;
  environmentName: string;
}

export class ContainerRegistryStack extends Stack {
  constructor(
    scope: Construct,
    id: string,
    props: ContainerRegistryStackProps,
  ) {
    super(scope, id, props);

    const resourceNamePrefix = `${props.applicationName}-${props.environmentName}`;

    Tags.of(this).add("application", props.applicationName);
    Tags.of(this).add("environment", props.environmentName);
    Tags.of(this).add("managed-by", "aws-cdk");
    Tags.of(this).add("component", "container-registry");
  }
}
