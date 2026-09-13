import { Stack, StackProps, Tags } from "aws-cdk-lib";
import { Construct } from "constructs";

interface StorageStackProps extends StackProps {
  applicationName: string;
  environmentName: string;
}

export class StorageStack extends Stack {
  constructor(scope: Construct, id: string, props: StorageStackProps) {
    super(scope, id, props);

    const resourceNamePrefix = `${props.applicationName}-${props.environmentName}`;

    Tags.of(this).add("application", props.applicationName);
    Tags.of(this).add("environment", props.environmentName);
    Tags.of(this).add("managed-by", "aws-cdk");
    Tags.of(this).add("component", "storage");
  }
}
