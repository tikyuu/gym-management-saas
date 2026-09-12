import { aws_ec2 as ec2 } from "aws-cdk-lib";
import { Construct } from "constructs";

interface SecurityGroupConstructProps {
  vpc: ec2.IVpc;
  resourceNamePrefix: string;
}

export class SecurityGroupConstruct extends Construct {
  public readonly albSecurityGroup: ec2.SecurityGroup;
  public readonly ecsSecurityGroup: ec2.SecurityGroup;
  public readonly rdsSecurityGroup: ec2.SecurityGroup;

  constructor(
    scope: Construct,
    id: string,
    props: SecurityGroupConstructProps,
  ) {
    super(scope, id);

    this.albSecurityGroup = new ec2.SecurityGroup(this, "AlbSecurityGroup", {
      allowAllOutbound: true,
      description: "Security group for the internal Application Load Balancer",
      securityGroupName: `${props.resourceNamePrefix}-alb-sg`,
      vpc: props.vpc,
    });

    this.ecsSecurityGroup = new ec2.SecurityGroup(this, "EcsSecurityGroup", {
      allowAllOutbound: true,
      description: "Security group for the ECS tasks",
      securityGroupName: `${props.resourceNamePrefix}-ecs-sg`,
      vpc: props.vpc,
    });

    this.ecsSecurityGroup.addIngressRule(
      this.albSecurityGroup,
      ec2.Port.tcp(8000),
      "Allow traffic from the internal ALB",
    );

    this.rdsSecurityGroup = new ec2.SecurityGroup(this, "RdsSecurityGroup", {
      allowAllOutbound: true,
      description: "Security group for the RDS database",
      securityGroupName: `${props.resourceNamePrefix}-rds-sg`,
      vpc: props.vpc,
    });
  }
}
