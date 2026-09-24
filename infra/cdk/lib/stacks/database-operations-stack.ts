import { Stack, StackProps, aws_ecr as ecr } from "aws-cdk-lib";
import { Construct } from "constructs";

interface DatabaseOperationsStackProps extends StackProps {
  repository: ecr.IRepository;
}

export class DatabaseOperationsStack extends Stack {
  constructor(scope: Construct, id: string, props: DatabaseOperationsStackProps) {
    super(scope, id, props);
  }
}
