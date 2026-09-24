import {
  Stack,
  StackProps,
  aws_ecr as ecr,
  aws_secretsmanager as secretsmanager,
} from "aws-cdk-lib";
import { Construct } from "constructs";

interface DatabaseOperationsStackProps extends StackProps {
  applicationUserSecret: secretsmanager.ISecret;
  databaseHost: string;
  databaseName: string;
  masterUserSecretArn: string;
  migrationUserSecret: secretsmanager.ISecret;
  repository: ecr.IRepository;
}

export class DatabaseOperationsStack extends Stack {
  constructor(scope: Construct, id: string, props: DatabaseOperationsStackProps) {
    super(scope, id, props);
  }
}
