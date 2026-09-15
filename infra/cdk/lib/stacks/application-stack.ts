import {
  CfnParameter,
  Stack,
  StackProps,
  Tags,
  aws_certificatemanager as acm,
  aws_ec2 as ec2,
  aws_ecr as ecr,
  aws_ecs as ecs,
  aws_elasticloadbalancingv2 as elbv2,
} from "aws-cdk-lib";
import { Construct } from "constructs";

interface ApplicationStackProps extends StackProps {
  albSecurityGroup: ec2.ISecurityGroup;
  applicationName: string;
  applicationSubnets: ec2.ISubnet[];
  apiDesiredCount: number;
  certificate: acm.ICertificate;
  ecsSecurityGroup: ec2.ISecurityGroup;
  environmentName: string;
  internalAlbSubnets: ec2.ISubnet[];
  repository: ecr.IRepository;
  taskCpu: number;
  taskMemoryMiB: number;
  vpc: ec2.IVpc;
}

export class ApplicationStack extends Stack {
  public readonly cluster: ecs.ICluster;
  public readonly loadBalancer: elbv2.IApplicationLoadBalancer;

  constructor(scope: Construct, id: string, props: ApplicationStackProps) {
    super(scope, id, props);

    const resourceNamePrefix = `${props.applicationName}-${props.environmentName}`;

    const apiImageTag = new CfnParameter(this, "ApiImageTag", {
      description: "Git commit SHA used as the FastAPI ECR image tag",
      type: "String",
    });

    Tags.of(this).add("application", props.applicationName);
    Tags.of(this).add("environment", props.environmentName);
    Tags.of(this).add("managed-by", "aws-cdk");
    Tags.of(this).add("component", "application");

    this.cluster = new ecs.Cluster(this, "Cluster", {
      clusterName: `${resourceNamePrefix}-ecs-cluster`,
      vpc: props.vpc,
    });

    this.loadBalancer = new elbv2.ApplicationLoadBalancer(this, "InternalAlb", {
      internetFacing: false,
      loadBalancerName: `${resourceNamePrefix}-internal-alb`,
      securityGroup: props.albSecurityGroup,
      vpc: props.vpc,
      vpcSubnets: {
        subnets: props.internalAlbSubnets,
      },
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

    const apiService = new ecs.FargateService(this, "ApiService", {
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
