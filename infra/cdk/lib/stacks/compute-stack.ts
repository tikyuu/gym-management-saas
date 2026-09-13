import { Stack, StackProps, Tags } from "aws-cdk-lib";
import { Construct } from "constructs";

interface ComputeStackProps extends StackProps {
  applicationName: string;
  environmentName: string;
}

export class ComputeStack extends Stack {
  constructor(scope: Construct, id: string, props: ComputeStackProps) {
    super(scope, id, props);

    Tags.of(this).add("application", props.applicationName);
    Tags.of(this).add("environment", props.environmentName);
    Tags.of(this).add("managed-by", "aws-cdk");
    Tags.of(this).add("component", "compute");
  }
}
