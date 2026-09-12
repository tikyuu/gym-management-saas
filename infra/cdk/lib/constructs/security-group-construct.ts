import { aws_ec2 as ec2 } from "aws-cdk-lib";
import { Construct } from "constructs";

interface SecurityGroupConstructProps {
  vpc: ec2.IVpc;
  resourceNamePrefix: string;
}

export class SecurityGroupConstruct extends Construct {
  constructor(
    scope: Construct,
    id: string,
    props: SecurityGroupConstructProps,
  ) {
    super(scope, id);
  }
}
