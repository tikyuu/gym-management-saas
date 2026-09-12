import { Stack, StackProps, aws_ec2 as ec2 } from "aws-cdk-lib";
import { Construct } from "constructs";

interface DatabaseStackProps extends StackProps {
  databaseSubnetIds: string[];
  vpc: ec2.IVpc;
}

export class DatabaseStack extends Stack {
  constructor(scope: Construct, id: string, props: DatabaseStackProps) {
    super(scope, id, props);
  }
}
