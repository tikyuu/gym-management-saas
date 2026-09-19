import {
  Aws,
  CfnParameter,
  Duration,
  RemovalPolicy,
  Stack,
  StackProps,
  Tags,
  aws_certificatemanager as acm,
  aws_ec2 as ec2,
  aws_ecr as ecr,
  aws_ecs as ecs,
  aws_elasticloadbalancingv2 as elbv2,
  aws_logs as logs,
  aws_s3 as s3,
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

    const apiLogGroup = new logs.LogGroup(this, "ApiLogGroup", {
      logGroupName: `/ecs/${resourceNamePrefix}-api`,
      removalPolicy: RemovalPolicy.DESTROY,
      retention: logs.RetentionDays.TWO_MONTHS,
    });

    const albAccessLogBucket = new s3.Bucket(this, "AlbAccessLogBucket", {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      bucketName: `${resourceNamePrefix}-${Aws.ACCOUNT_ID}-alb-access-logs-s3`,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      lifecycleRules: [
        {
          expiration: Duration.days(60),
        },
      ],
      objectOwnership: s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
      removalPolicy: RemovalPolicy.RETAIN,
    });

    this.cluster = new ecs.Cluster(this, "Cluster", {
      clusterName: `${resourceNamePrefix}-ecs-cluster`,
      vpc: props.vpc,
    });

    const loadBalancer = new elbv2.ApplicationLoadBalancer(this, "InternalAlb", {
      internetFacing: false,
      loadBalancerName: `${resourceNamePrefix}-internal-alb`,
      securityGroup: props.albSecurityGroup,
      vpc: props.vpc,
      vpcSubnets: {
        subnets: props.internalAlbSubnets,
      },
    });

    loadBalancer.logAccessLogs(albAccessLogBucket);
    this.loadBalancer = loadBalancer;

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
      logging: ecs.LogDrivers.awsLogs({
        logGroup: apiLogGroup,
        streamPrefix: "api",
      }),
      portMappings: [{ containerPort: 8000 }],
    });

    const apiService = new ecs.FargateService(this, "ApiService", {
      assignPublicIp: false,
      cluster: this.cluster,
      circuitBreaker: {
        rollback: true,
      },
      desiredCount: props.apiDesiredCount,
      healthCheckGracePeriod: Duration.seconds(60),
      maxHealthyPercent: 200,
      minHealthyPercent: 100,
      securityGroups: [props.ecsSecurityGroup],
      serviceName: `${resourceNamePrefix}-api-service`,
      taskDefinition,
      vpcSubnets: { subnets: props.applicationSubnets },
    });

    const apiTargetGroup = new elbv2.ApplicationTargetGroup(
      this,
      "ApiTargetGroup",
      {
        healthCheck: {
          healthyThresholdCount: 2,
          path: "/health",
        },
        port: 8000,
        protocol: elbv2.ApplicationProtocol.HTTP,
        targetGroupName: `${resourceNamePrefix}-api-tg`,
        targets: [apiService],
        vpc: props.vpc,
      },
    );

    this.loadBalancer.addListener("HttpsListener", {
      certificates: [props.certificate],
      defaultTargetGroups: [apiTargetGroup],
      open: false,
      port: 443,
      protocol: elbv2.ApplicationProtocol.HTTPS,
      sslPolicy: elbv2.SslPolicy.RECOMMENDED_TLS,
    });
  }
}
