import { Stack, StackProps } from "aws-cdk-lib";
import * as ecs from "aws-cdk-lib/aws-ecs";
import * as iam from "aws-cdk-lib/aws-iam";
import { Construct } from "constructs";

export class CiCdIdentityStack extends Stack {
  private readonly gitHubDevDeployRole: iam.Role;

  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    const gitHubProvider = new iam.OpenIdConnectProvider(this, "GitHubOidcProvider", {
      url: "https://token.actions.githubusercontent.com",
      clientIds: ["sts.amazonaws.com"],
    });

    this.gitHubDevDeployRole = new iam.Role(this, "GitHubDevDeployRole", {
      assumedBy: new iam.OpenIdConnectPrincipal(gitHubProvider, {
        StringEquals: {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          "token.actions.githubusercontent.com:sub":
            "repo:tikyuu@224914317/gym-management-saas@1350988028:environment:development",
          "token.actions.githubusercontent.com:ref": "refs/heads/main",
        },
      }),
      roleName: "gym-management-dev-github-deploy-role",
    });

    this.gitHubDevDeployRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["sts:AssumeRole"],
        resources: [
          "arn:aws:iam::526811500752:role/cdk-hnb659fds-deploy-role-526811500752-ap-northeast-1",
          "arn:aws:iam::526811500752:role/cdk-hnb659fds-deploy-role-526811500752-us-east-1",
          "arn:aws:iam::526811500752:role/cdk-hnb659fds-file-publishing-role-526811500752-ap-northeast-1",
        ],
      }),
    );

    this.gitHubDevDeployRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["ecr:GetAuthorizationToken"],
        resources: ["*"],
      }),
    );

    this.gitHubDevDeployRole.addToPolicy(
      new iam.PolicyStatement({
        actions: [
          "ecr:BatchCheckLayerAvailability",
          "ecr:BatchGetImage",
          "ecr:CompleteLayerUpload",
          "ecr:InitiateLayerUpload",
          "ecr:PutImage",
          "ecr:UploadLayerPart",
        ],
        resources: [
          this.formatArn({
            service: "ecr",
            resource: "repository",
            resourceName: "gym-management-dev-api-ecr",
          }),
        ],
      }),
    );

    this.gitHubDevDeployRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["ecs:RunTask"],
        conditions: {
          ArnEquals: {
            "ecs:cluster": this.formatArn({
              service: "ecs",
              resource: "cluster",
              resourceName: "gym-management-dev-ecs-cluster",
            }),
          },
        },
        resources: [
          this.formatArn({
            service: "ecs",
            resource: "task-definition",
            resourceName: "gym-management-dev-db-bootstrap:*",
          }),
        ],
      }),
    );
  }

  public grantDatabaseBootstrapPassRole(taskDefinition: ecs.FargateTaskDefinition): void {
    this.gitHubDevDeployRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["iam:PassRole"],
        conditions: {
          StringEquals: {
            "iam:PassedToService": "ecs-tasks.amazonaws.com",
          },
        },
        resources: [
          taskDefinition.taskRole.roleArn,
          taskDefinition.obtainExecutionRole().roleArn,
        ],
      }),
    );
  }
}
