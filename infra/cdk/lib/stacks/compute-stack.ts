import {
  CfnParameter,
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
  applicationSubnets: ec2.ISubnet[];
  apiDesiredCount: number;
  ecsSecurityGroup: ec2.ISecurityGroup;
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

    const apiImageTag = new CfnParameter(this, "ApiImageTag", {
      description: "Git commit SHA used as the FastAPI ECR image tag",
      type: "String",
    });

    Tags.of(this).add("application", props.applicationName);
    Tags.of(this).add("environment", props.environmentName);
    Tags.of(this).add("managed-by", "aws-cdk");
    Tags.of(this).add("component", "compute");

    this.cluster = new ecs.Cluster(this, "Cluster", {
      clusterName: `${resourceNamePrefix}-ecs-cluster`,
      vpc: props.vpc,
    });

    const taskDefinition = new ecs.FargateTaskDefinition(
      this,
      "ApiTaskDefinition",
      {
        cpu: props.taskCpu,
        family: `${resourceNamePrefix}-api-task`,
        memoryLimitMiB: props.taskMemoryMiB,
      },
    );

    taskDefinition.addContainer("ApiContainer", {
      containerName: `${resourceNamePrefix}-api-container`,
      essential: true,
      image: ecs.ContainerImage.fromEcrRepository(
        props.repository,
        apiImageTag.valueAsString,
      ),
      portMappings: [{ containerPort: 8000 }],
    });

    new ecs.FargateService(this, "ApiService", {
      assignPublicIp: false,
      cluster: this.cluster,
      circuitBreaker: {
        rollback: true,
      },
      desiredCount: props.apiDesiredCount,
      maxHealthyPercent: 200,
      minHealthyPercent: 100,
      securityGroups: [props.ecsSecurityGroup],
      serviceName: `${resourceNamePrefix}-api-service`,
      taskDefinition,
      vpcSubnets: { subnets: props.applicationSubnets },
    });
  }
}
