import {
  Stack,
  StackProps,
  Tags,
  aws_ec2 as ec2,
  aws_ecr as ecr,
  aws_ecs as ecs,
} from "aws-cdk-lib";
import { Construct } from "constructs";

interface ComputeStackProps extends StackProps {
  applicationName: string;
  environmentName: string;
  repository: ecr.IRepository;
  taskCpu: number;
  taskMemoryMiB: number;
  vpc: ec2.IVpc;
}

export class ComputeStack extends Stack {
  public readonly cluster: ecs.ICluster;

  constructor(scope: Construct, id: string, props: ComputeStackProps) {
    super(scope, id, props);

    const resourceNamePrefix = `${props.applicationName}-${props.environmentName}`;

    Tags.of(this).add("application", props.applicationName);
    Tags.of(this).add("environment", props.environmentName);
    Tags.of(this).add("managed-by", "aws-cdk");
    Tags.of(this).add("component", "compute");

    this.cluster = new ecs.Cluster(this, "Cluster", {
      clusterName: `${resourceNamePrefix}-ecs-cluster`,
      vpc: props.vpc,
    });
  }
}
