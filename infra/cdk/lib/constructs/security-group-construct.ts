import { aws_ec2 as ec2 } from "aws-cdk-lib";
import { Construct } from "constructs";

interface SecurityGroupConstructProps {
  vpc: ec2.IVpc;
  resourceNamePrefix: string;
}

export class SecurityGroupConstruct extends Construct {
  public readonly albSecurityGroup: ec2.SecurityGroup;

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
  }
}
