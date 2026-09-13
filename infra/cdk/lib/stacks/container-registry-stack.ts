import { Stack, StackProps, Tags, aws_ecr as ecr } from "aws-cdk-lib";
import { Construct } from "constructs";

interface ContainerRegistryStackProps extends StackProps {
  applicationName: string;
  environmentName: string;
}

export class ContainerRegistryStack extends Stack {
  public readonly repository: ecr.IRepository;

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

    this.repository = new ecr.Repository(this, "ApiRepository", {
      imageScanOnPush: true,
      imageTagMutability: ecr.TagMutability.IMMUTABLE,
      repositoryName: `${resourceNamePrefix}-api-ecr`,
    });
  }
}
