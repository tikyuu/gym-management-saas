import {
  CfnParameter,
  Stack,
  StackProps,
  aws_ecr as ecr,
  aws_ecs as ecs,
  aws_secretsmanager as secretsmanager,
} from "aws-cdk-lib";
import { Construct } from "constructs";

interface DatabaseOperationsStackProps extends StackProps {
  applicationUserSecret: secretsmanager.ISecret;
  databaseBootstrapTaskCpu: number;
  databaseBootstrapTaskMemoryMiB: number;
  databaseHost: string;
  databaseName: string;
  masterUserSecretArn: string;
  migrationUserSecret: secretsmanager.ISecret;
  repository: ecr.IRepository;
}

export class DatabaseOperationsStack extends Stack {
  constructor(scope: Construct, id: string, props: DatabaseOperationsStackProps) {
    super(scope, id, props);

    const databaseBootstrapImageTag = new CfnParameter(this, "DatabaseBootstrapImageTag", {
      description: "Git commit SHA used as the DB bootstrap ECR image tag",
      type: "String",
    });

    const taskDefinition = new ecs.FargateTaskDefinition(this, "DatabaseBootstrapTaskDefinition", {
      cpu: props.databaseBootstrapTaskCpu,
      memoryLimitMiB: props.databaseBootstrapTaskMemoryMiB,
    });

    taskDefinition.addContainer("DatabaseBootstrapContainer", {
      command: ["/app/.venv/bin/python", "-m", "app.bootstrap_db"],
      image: ecs.ContainerImage.fromEcrRepository(
        props.repository,
        databaseBootstrapImageTag.valueAsString,
      ),
    });
  }
}
